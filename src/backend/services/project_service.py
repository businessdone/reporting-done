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
from database.repositories.repository import Repository
from backend.services.pagination_service import PaginationService


class ProjectService:
    __slots__ = ("_paginator",)

    def __init__(self, paginator: PaginationService) -> None:
        self._paginator = paginator

    def create(
        self,
        data: ProjectCreateDTO,
        session: AsyncSession,
    ) -> Result[ProjectDTO, str]:
        with session as s:
            repo = Repository(s, Project)

            existing = repo.query(name=data.name)
            if existing:
                return Err(f"Project with name '{data.name}' already exists")

            new_project = Project(
                id=str(ULID()),
                name=data.name,
                email=data.email,
                send_email=data.send_email,
                archived=data.archived,
                developers=[],
                tasks=[],
            )

            repo.create(new_project)

            return Ok(ProjectDTO.model_validate(new_project.to_dict()))

    def get_by_id(
        self,
        project_id: str,
        session: AsyncSession,
    ) -> Result[ProjectDTO, str]:
        with session as s:
            repo = Repository(s, Project)
            projects = repo.query(
                id=project_id,
                options=[Project.developers, Project.tasks],
            )

            if not projects:
                return Err(f"Project with id '{project_id}' not found")

            return Ok(ProjectDTO.model_validate(projects[0].to_dict()))

    def update(
        self,
        project_id: str,
        data: ProjectUpdateDTO,
        session: AsyncSession,
    ) -> Result[ProjectDTO, str]:
        with session as s:
            repo = Repository(s, Project)
            project = repo.get(project_id)

            if not project:
                return Err(f"Project with id '{project_id}' not found")

            update_data = data.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if value is not None:
                    setattr(project, field, value)

            s.commit()

            updated = repo.query(
                id=project_id,
                options=[Project.developers, Project.tasks],
            )

            return Ok(ProjectDTO.model_validate(updated[0].to_dict()))

    def delete(
        self,
        project_id: str,
        session: AsyncSession,
    ) -> Result[None, str]:
        with session as s:
            repo = Repository(s, Project)
            task_repo = Repository(s, Task)

            project = repo.get(project_id)

            if not project:
                return Err(f"Project with id '{project_id}' not found")

            tasks = task_repo.query(project_id=project_id, limit=1)
            if tasks:
                return Err("Cannot delete project with associated tasks")

            repo.delete(project)
            s.commit()

            return Ok(None)

    def list_all(
        self,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[ProjectDTO]:
        with session as s:
            repo = Repository(s, Project)

            total = repo.count(**filters)
            meta = self._paginator.calculate(total, pagination)

            if total == 0:
                return PaginatedResult(items=[], meta=meta)

            projects = repo.query(
                limit=meta.per_page,
                offset=(meta.current_page - 1) * meta.per_page,
                options=[Project.developers, Project.tasks],
                **filters,
            )

            items = [ProjectDTO.model_validate(p.to_dict()) for p in projects]

            return PaginatedResult(items=items, meta=meta)

    def list_for_user(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[ProjectDTO]:
        with session as s:
            assoc_repo = Repository(s, ProjectUser)
            project_repo = Repository(s, Project)

            associations = assoc_repo.query(user_id=user_id)
            project_ids = [a.project_id for a in associations]

            if not project_ids:
                meta = self._paginator.calculate(0, pagination)
                return PaginatedResult(items=[], meta=meta)

            total = len(project_ids)
            meta = self._paginator.calculate(total, pagination)

            projects = project_repo.query(
                in_={Project.id: project_ids},
                options=[Project.developers, Project.tasks],
                **filters,
            )

            items = [ProjectDTO.model_validate(p.to_dict()) for p in projects]

            return PaginatedResult(items=items, meta=meta)

    def assign_user(
        self,
        project_id: str,
        user_id: str,
        session: AsyncSession,
    ) -> Result[ProjectDTO, str]:
        with session as s:
            project_repo = Repository(s, Project)
            user_repo = Repository(s, User)
            assoc_repo = Repository(s, ProjectUser)

            project = project_repo.get(project_id)
            if not project:
                return Err(f"Project with id '{project_id}' not found")

            user = user_repo.get(user_id)
            if not user:
                return Err(f"User with id '{user_id}' not found")

            existing = assoc_repo.query(project_id=project_id, user_id=user_id)
            if existing:
                return Err("User is already assigned to this project")

            assoc_repo.create(
                ProjectUser(
                    id=str(ULID()),
                    project_id=project_id,
                    user_id=user_id,
                )
            )

            updated = project_repo.query(
                id=project_id,
                options=[Project.developers, Project.tasks],
            )

            return Ok(ProjectDTO.model_validate(updated[0].to_dict()))

    def remove_user(
        self,
        project_id: str,
        user_id: str,
        session: AsyncSession,
    ) -> Result[ProjectDTO, str]:
        with session as s:
            project_repo = Repository(s, Project)
            user_repo = Repository(s, User)
            assoc_repo = Repository(s, ProjectUser)

            project = project_repo.get(project_id)
            if not project:
                return Err(f"Project with id '{project_id}' not found")

            user = user_repo.get(user_id)
            if not user:
                return Err(f"User with id '{user_id}' not found")

            associations = assoc_repo.query(
                project_id=project_id, user_id=user_id
            )
            if not associations:
                return Err("User is not assigned to this project")

            assoc_repo.delete(associations[0])

            updated = project_repo.query(
                id=project_id,
                options=[Project.developers, Project.tasks],
            )

            return Ok(ProjectDTO.model_validate(updated[0].to_dict()))

    def get_project_users(
        self,
        project_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
    ) -> PaginatedResult[UserDTO]:
        with session as s:
            assoc_repo = Repository(s, ProjectUser)
            user_repo = Repository(s, User)

            total = assoc_repo.count(project_id=project_id)
            meta = self._paginator.calculate(total, pagination)

            if total == 0:
                return PaginatedResult(items=[], meta=meta)

            associations = assoc_repo.query(
                project_id=project_id,
                limit=meta.per_page,
                offset=(meta.current_page - 1) * meta.per_page,
            )

            user_ids = [a.user_id for a in associations]
            users = user_repo.query(
                in_={User.id: user_ids},
                options=[User.tasks, User.projects],
            )

            items = [UserDTO.model_validate(u.to_dict()) for u in users]

            return PaginatedResult(items=items, meta=meta)

    def get_project_tasks(
        self,
        project_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
    ) -> PaginatedResult[TaskDTO]:
        with session as s:
            repo = Repository(s, Task)

            total = repo.count(project_id=project_id)
            meta = self._paginator.calculate(total, pagination)

            if total == 0:
                return PaginatedResult(items=[], meta=meta)

            tasks = repo.query(
                project_id=project_id,
                limit=meta.per_page,
                offset=(meta.current_page - 1) * meta.per_page,
                options=[Task.logs],
            )

            items = [TaskDTO.model_validate(t.to_dict()) for t in tasks]

            return PaginatedResult(items=items, meta=meta)
