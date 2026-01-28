from typing import Any
from datetime import datetime

from ulid import ULID

from backend.types.result import Result, Ok, Err
from backend.types.pagination import PaginationParams, PaginatedResult
from backend.types.dtos import TaskCreateDTO, TaskUpdateDTO, TaskDTO, LogDTO
from backend.services.pagination_service import PaginationService
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User, Task, Log, Project
from businessdone_core.database import Repository


class TaskService:
    __slots__ = ("_paginator",)

    def __init__(self, paginator: PaginationService) -> None:
        self._paginator = paginator

    async def create(
        self,
        data: TaskCreateDTO,
        user_id: str,
        session: AsyncSession,
    ) -> Result[TaskDTO, str]:
        project_repo = Repository(session, Project)
        user_repo = Repository(session, User)
        task_repo = Repository(session, Task)

        project = await project_repo.get(data.project_id)
        if not project:
            return Err(f"Project with id '{data.project_id}' not found")

        assigned_user_id = data.user_id or user_id
        user = await user_repo.get(assigned_user_id)
        if not user:
            return Err(f"User with id '{assigned_user_id}' not found")

        new_task = Task(
            id=str(ULID()),
            project_id=project.id,
            project_name=project.name,
            user_id=user.id,
            user_name=user.full_name,
            title=data.title,
            hours_required=data.hours_required,
            hours_worked=0.0,
            returned=False,
            description=data.description,
            status=data.status,
            created_at=datetime.now(),
            logs=[],
        )

        await task_repo.create(new_task)
        await session.commit()

        return Ok(TaskDTO.model_validate(new_task.to_dict()))

    async def get_by_id(
        self,
        task_id: str,
        session: AsyncSession,
    ) -> Result[TaskDTO, str]:
        repo = Repository(session, Task)
        tasks = await repo.query(id=task_id, options=[Task.logs])

        if not tasks:
            return Err(f"Task with id '{task_id}' not found")

        return Ok(TaskDTO.model_validate(tasks[0].to_dict()))

    async def update(
        self,
        task_id: str,
        data: TaskUpdateDTO,
        user_id: str,
        is_admin: bool,
        session: AsyncSession,
    ) -> Result[TaskDTO, str]:
        repo = Repository(session, Task)
        task = await repo.get(task_id)

        if not task:
            return Err(f"Task with id '{task_id}' not found")

        if not is_admin and task.user_id != user_id:
            return Err("Not authorized to update this task")

        if data.user_id and data.user_id != task.user_id and not is_admin:
            return Err("Not authorized to reassign task")

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(task, field, value)

        task.updated_at = datetime.now()

        await session.commit()

        updated = await repo.query(id=task_id, options=[Task.logs])

        return Ok(TaskDTO.model_validate(updated[0].to_dict()))

    async def delete(
        self,
        task_id: str,
        session: AsyncSession,
    ) -> Result[None, str]:
        task_repo = Repository(session, Task)
        log_repo = Repository(session, Log)

        task = await task_repo.get(task_id)
        if not task:
            return Err(f"Task with id '{task_id}' not found")

        logs = await log_repo.query(task_id=task_id)
        for log in logs:
            await log_repo.delete(log)

        await task_repo.delete(task)
        await session.commit()

        return Ok(None)

    async def list_all(
        self,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[TaskDTO]:
        repo = Repository(session, Task)

        total = await repo.count(**filters)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        tasks = await repo.query(
            limit=meta.per_page,
            offset=(meta.current_page - 1) * meta.per_page,
            options=[Task.logs],
            **filters,
        )

        items = [TaskDTO.model_validate(t.to_dict()) for t in tasks]

        return PaginatedResult(items=items, meta=meta)

    async def list_for_user(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[TaskDTO]:
        combined_filters = {**filters, "user_id": user_id}
        return await self.list_all(pagination, session, **combined_filters)

    async def get_task_logs(
        self,
        task_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
    ) -> PaginatedResult[LogDTO]:
        repo = Repository(session, Log)

        total = await repo.count(task_id=task_id)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        logs = await repo.query(
            task_id=task_id,
            limit=meta.per_page,
            offset=(meta.current_page - 1) * meta.per_page,
        )

        items = [LogDTO.model_validate(log.to_dict()) for log in logs]

        return PaginatedResult(items=items, meta=meta)

