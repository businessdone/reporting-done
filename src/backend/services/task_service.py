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
    
    def create(
        self,
        data: TaskCreateDTO,
        user_id: str,
        session: AsyncSession,
    ) -> Result[TaskDTO, str]:
        with session as s:
            project_repo = Repository(s, Project)
            user_repo = Repository(s, User)
            task_repo = Repository(s, Task)
            
            project = project_repo.get(data.project_id)
            if not project:
                return Err(f"Project with id '{data.project_id}' not found")
            
            assigned_user_id = data.user_id or user_id
            user = user_repo.get(assigned_user_id)
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
            
            task_repo.create(new_task)
            s.commit()
            
            return Ok(TaskDTO.model_validate(new_task.to_dict()))
    
    def get_by_id(
        self,
        task_id: str,
        session: AsyncSession,
    ) -> Result[TaskDTO, str]:
        with session as s:
            repo = Repository(s, Task)
            tasks = repo.query(id=task_id, options=[Task.logs])
            
            if not tasks:
                return Err(f"Task with id '{task_id}' not found")
            
            return Ok(TaskDTO.model_validate(tasks[0].to_dict()))
    
    def update(
        self,
        task_id: str,
        data: TaskUpdateDTO,
        user_id: str,
        is_admin: bool,
        session: AsyncSession,
    ) -> Result[TaskDTO, str]:
        with session as s:
            repo = Repository(s, Task)
            task = repo.get(task_id)
            
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
            
            s.commit()
            
            updated = repo.query(id=task_id, options=[Task.logs])
            
            return Ok(TaskDTO.model_validate(updated[0].to_dict()))
    
    def delete(
        self,
        task_id: str,
        session: AsyncSession,
    ) -> Result[None, str]:
        with session as s:
            task_repo = Repository(s, Task)
            log_repo = Repository(s, Log)
            
            task = task_repo.get(task_id)
            if not task:
                return Err(f"Task with id '{task_id}' not found")
            
            logs = log_repo.query(task_id=task_id)
            for log in logs:
                log_repo.delete(log)
            
            task_repo.delete(task)
            s.commit()
            
            return Ok(None)
    
    def list_all(
        self,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[TaskDTO]:
        with session as s:
            repo = Repository(s, Task)
            
            total = repo.count(**filters)
            meta = self._paginator.calculate(total, pagination)
            
            if total == 0:
                return PaginatedResult(items=[], meta=meta)
            
            tasks = repo.query(
                limit=meta.per_page,
                offset=(meta.current_page - 1) * meta.per_page,
                options=[Task.logs],
                **filters,
            )
            
            items = [TaskDTO.model_validate(t.to_dict()) for t in tasks]
            
            return PaginatedResult(items=items, meta=meta)
    
    def list_for_user(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[TaskDTO]:
        combined_filters = {**filters, "user_id": user_id}
        return self.list_all(pagination, session, **combined_filters)
    
    def get_task_logs(
        self,
        task_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
    ) -> PaginatedResult[LogDTO]:
        with session as s:
            repo = Repository(s, Log)
            
            total = repo.count(task_id=task_id)
            meta = self._paginator.calculate(total, pagination)
            
            if total == 0:
                return PaginatedResult(items=[], meta=meta)
            
            logs = repo.query(
                task_id=task_id,
                limit=meta.per_page,
                offset=(meta.current_page - 1) * meta.per_page,
            )
            
            items = [LogDTO.model_validate(log.to_dict()) for log in logs]
            
            return PaginatedResult(items=items, meta=meta)

