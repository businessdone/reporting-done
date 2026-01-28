from typing import Any
from datetime import datetime, timezone
from io import StringIO
import csv

from ulid import ULID

from backend.types.result import Result, Ok, Err
from backend.types.pagination import PaginationParams, PaginatedResult
from backend.types.dtos import LogCreateDTO, LogUpdateDTO, LogDTO
from backend.services.pagination_service import PaginationService
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User, Task, Log
from core.enums.task_status import TaskStatus
from businessdone_core.database import Repository


class LogService:
    __slots__ = ("_paginator",)

    def __init__(self, paginator: PaginationService) -> None:
        self._paginator = paginator

    async def create(
        self,
        data: LogCreateDTO,
        user_id: str,
        session: AsyncSession,
    ) -> Result[LogDTO, str]:
        task_repo = Repository(session, Task)
        user_repo = Repository(session, User)
        log_repo = Repository(session, Log)

        task = await task_repo.get(data.task_id)
        if not task:
            return Err(f"Task with id '{data.task_id}' not found")

        user = await user_repo.get(user_id)
        if not user:
            return Err(f"User with id '{user_id}' not found")

        was_done = task._status == TaskStatus.DONE
        new_status = TaskStatus(data.task_status) if data.task_status else None

        if was_done and new_status and new_status != TaskStatus.DONE:
            task.returned = True

        task.hours_worked += data.hours_spent
        task.status = data.task_status
        task.updated_at = datetime.now(timezone.utc)
        await task_repo.update(task)

        new_log = Log(
            id=str(ULID()),
            created_at=datetime.now(timezone.utc),
            task_id=task.id,
            task_name=task.title,
            description=data.description,
            user_id=user.id,
            user_name=user.full_name,
            project_id=task.project_id,
            project_name=task.project_name,
            hours_spent=data.hours_spent,
            task_status=data.task_status,
        )

        await log_repo.create(new_log)
        await session.commit()

        return Ok(LogDTO.model_validate(new_log.to_dict()))

    async def get_by_id(
        self,
        log_id: str,
        session: AsyncSession,
    ) -> Result[LogDTO, str]:
        repo = Repository(session, Log)
        logs = await repo.query(id=log_id)

        if not logs:
            return Err(f"Log with id '{log_id}' not found")

        return Ok(LogDTO.model_validate(logs[0].to_dict()))

    async def update(
        self,
        log_id: str,
        data: LogUpdateDTO,
        user_id: str,
        is_admin: bool,
        session: AsyncSession,
    ) -> Result[LogDTO, str]:
        repo = Repository(session, Log)
        task_repo = Repository(session, Task)

        log = await repo.get(log_id)
        if not log:
            return Err(f"Log with id '{log_id}' not found")

        if not is_admin and log.user_id != user_id:
            return Err("Not authorized to update this log")

        old_hours = log.hours_spent
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(log, field, value)

        if data.hours_spent is not None:
            task = await task_repo.get(log.task_id)
            if task:
                hours_diff = data.hours_spent - old_hours
                task.hours_worked += hours_diff
                if task.hours_worked < 0:
                    task.hours_worked = 0
                await task_repo.update(task)

        if data.task_status is not None:
            task = await task_repo.get(log.task_id)
            if task:
                task.status = data.task_status
                await task_repo.update(task)

        await session.commit()

        return Ok(LogDTO.model_validate(log.to_dict()))

    async def delete(
        self,
        log_id: str,
        user_id: str,
        is_admin: bool,
        session: AsyncSession,
    ) -> Result[None, str]:
        repo = Repository(session, Log)
        task_repo = Repository(session, Task)

        log = await repo.get(log_id)
        if not log:
            return Err(f"Log with id '{log_id}' not found")

        if not is_admin and log.user_id != user_id:
            return Err("Not authorized to delete this log")

        task = await task_repo.get(log.task_id)
        if task:
            task.hours_worked -= log.hours_spent
            if task.hours_worked < 0:
                task.hours_worked = 0
            await task_repo.update(task)

        await repo.delete(log)
        await session.commit()

        return Ok(None)

    async def list_all(
        self,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[LogDTO]:
        repo = Repository(session, Log)

        total = await repo.count(**filters)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        logs = await repo.query(
            limit=meta.per_page,
            offset=(meta.current_page - 1) * meta.per_page,
            **filters,
        )

        items = [LogDTO.model_validate(log.to_dict()) for log in logs]

        return PaginatedResult(items=items, meta=meta)

    async def list_for_user(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[LogDTO]:
        combined_filters = {**filters, "user_id": user_id}
        return await self.list_all(pagination, session, **combined_filters)

    async def export_to_csv(
        self,
        session: AsyncSession,
        **filters: Any,
    ) -> Result[bytes, str]:
        repo = Repository(session, Log)
        logs = await repo.query(**filters)

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "ID",
            "Task Name",
            "User",
            "Task Status",
            "Hours Spent",
            "Date",
        ])

        for log in logs:
            writer.writerow([
                log.id,
                log.task_name,
                log.user_name,
                log.task_status,
                log.hours_spent,
                log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

        return Ok(output.getvalue().encode("utf-8"))
