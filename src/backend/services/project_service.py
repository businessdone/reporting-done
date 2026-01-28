from typing import Any

from ulid import ULID

from core.models import Task, User, Project
from backend.types.dtos import (
    TaskDTO,
    UserDTO,
    ProjectDTO,
    ProjectCreateDTO,
    ProjectUpdateDTO,
)
from backend.types.result import Ok, Err, Result
from backend.types.pagination import PaginatedResult, PaginationParams
from core.models.project_user import ProjectUser
from sqlalchemy.ext.asyncio import AsyncSession
from bd_core.database import Repository
from backend.services.pagination_service import PaginationService


class ProjectService:
    __slots__ = ("_paginator",)

    def __init__(self, paginator: PaginationService) -> None:
        self._paginator = paginator

    async def create(
        self,
        data: ProjectCreateDTO,
        session: AsyncSession,
    ) -> Result[ProjectDTO, str]:
        repo = Repository(session, Project)

        existing = await repo.query(name=data.name)
        if existing:
            return Err(f"Project with name '{data.name}' already exists")

        new_project = Project(              id=str(ULID()),
            name=data.name,
            email=data.email,
            send_email=data.send_email,
            archived=data.archived,
            developers=[],
            tasks=[],
        )

        await repo.create(new_project)
        await session.commit()

        return Ok(ProjectDTO.model_validate(new_project.to_dict()))

    async def get_by_id(
        self,
        project_id: str,
        session: AsyncSession,
    ) -> Result[ProjectDTO, str]:
        repo = Repository(session, Project)
        projects = await repo.query(
            id=project_id,
            options=[Project.developers, Project.tasks],          )

        if not projects:
            return Err(f"Project with id '{project_id}' not found")

        return Ok(ProjectDTO.model_validate(projects[0].to_dict()))

    async def update(
        self,
        project_id: str,
        data: ProjectUpdateDTO,
        session: AsyncSession,
    ) -> Result[ProjectDTO, str]:
        repo = Repository(session, Project)
        project = await repo.get(project_id)

        if not project:
            return Err(f"Project with id '{project_id}' not found")

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(project, field, value)

        await session.commit()

        updated = await repo.query(
            id=project_id,
            options=[Project.developers, Project.tasks],          )

        return Ok(ProjectDTO.model_validate(updated[0].to_dict()))

    async def delete(
        self,
        project_id: str,
        session: AsyncSession,
    ) -> Result[None, str]:
        repo = Repository(session, Project)
        task_repo = Repository(session, Task)

        project = await repo.get(project_id)

        if not project:
            return Err(f"Project with id '{project_id}' not found")

        tasks = await task_repo.query(project_id=project_id, limit=1)
        if tasks:
            return Err("Cannot delete project with associated tasks")

        await repo.delete(project)
        await session.commit()

        return Ok(None)

    async def list_all(
        self,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[ProjectDTO]:
        repo = Repository(session, Project)

        total = await repo.count(**filters)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        projects = await repo.query(
            limit=meta.per_page,
            offset=(meta.current_page - 1) * meta.per_page,
            options=[Project.developers, Project.tasks],              **filters,
        )

        items = [ProjectDTO.model_validate(p.to_dict()) for p in projects]

        return PaginatedResult(items=items, meta=meta)

    async def list_for_user(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[ProjectDTO]:
        assoc_repo = Repository(session, ProjectUser)
        project_repo = Repository(session, Project)

        associations = await assoc_repo.query(user_id=user_id)
        project_ids = [a.project_id for a in associations]

        if not project_ids:
            meta = self._paginator.calculate(0, pagination)
            return PaginatedResult(items=[], meta=meta)

        total = len(project_ids)
        meta = self._paginator.calculate(total, pagination)

        projects = await project_repo.query(
            in_={Project.id: project_ids},
            options=[Project.developers, Project.tasks],              **filters,
        )

        items = [ProjectDTO.model_validate(p.to_dict()) for p in projects]

        return PaginatedResult(items=items, meta=meta)

    async def assign_user(
        self,
        project_id: str,
        user_id: str,
        session: AsyncSession,
    ) -> Result[ProjectDTO, str]:
        project_repo = Repository(session, Project)
        user_repo = Repository(session, User)
        assoc_repo = Repository(session, ProjectUser)

        project = await project_repo.get(project_id)
        if not project:
            return Err(f"Project with id '{project_id}' not found")

        user = await user_repo.get(user_id)
        if not user:
            return Err(f"User with id '{user_id}' not found")

        existing = await assoc_repo.query(project_id=project_id, user_id=user_id)
        if existing:
            return Err("User is already assigned to this project")

        await assoc_repo.create(
            ProjectUser(
                id=str(ULID()),
                project_id=project_id,
                user_id=user_id,
            )
        )
        await session.commit()

        updated = await project_repo.query(
            id=project_id,
            options=[Project.developers, Project.tasks],
        )

        return Ok(ProjectDTO.model_validate(updated[0].to_dict()))

    async def remove_user(
        self,
        project_id: str,
        user_id: str,
        session: AsyncSession,
    ) -> Result[ProjectDTO, str]:
        project_repo = Repository(session, Project)
        user_repo = Repository(session, User)
        assoc_repo = Repository(session, ProjectUser)

        project = await project_repo.get(project_id)
        if not project:
            return Err(f"Project with id '{project_id}' not found")

        user = await user_repo.get(user_id)
        if not user:
            return Err(f"User with id '{user_id}' not found")

        associations = await assoc_repo.query(
            project_id=project_id, user_id=user_id
        )
        if not associations:
            return Err("User is not assigned to this project")

        await assoc_repo.delete(associations[0])
        await session.commit()

        updated = await project_repo.query(
            id=project_id,
            options=[Project.developers, Project.tasks],
        )

        return Ok(ProjectDTO.model_validate(updated[0].to_dict()))

    async def get_project_users(
        self,
        project_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
    ) -> PaginatedResult[UserDTO]:
        assoc_repo = Repository(session, ProjectUser)
        user_repo = Repository(session, User)

        total = await assoc_repo.count(project_id=project_id)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        associations = await assoc_repo.query(
            project_id=project_id,
            limit=meta.per_page,
            offset=(meta.current_page - 1) * meta.per_page,
        )

        user_ids = [a.user_id for a in associations]
        users = await user_repo.query(
            in_={User.id: user_ids},
            options=[User.tasks, User.projects],          )

        items = [UserDTO.model_validate(u.to_dict()) for u in users]

        return PaginatedResult(items=items, meta=meta)

    async def get_project_tasks(
        self,
        project_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
    ) -> PaginatedResult[TaskDTO]:
        repo = Repository(session, Task)

        total = await repo.count(project_id=project_id)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        tasks = await repo.query(
            project_id=project_id,
            limit=meta.per_page,
            offset=(meta.current_page - 1) * meta.per_page,
            options=[Task.logs],
        )

        items = [TaskDTO.model_validate(t.to_dict()) for t in tasks]

        return PaginatedResult(items=items, meta=meta)
