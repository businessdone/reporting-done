from typing import Any
from datetime import datetime

from ulid import ULID

from backend.types.result import Result, Ok, Err
from backend.types.pagination import PaginationParams, PaginatedResult
from backend.types.dtos import (
    UserCreateDTO,
    UserUpdateDTO,
    UserDTO,
    ProjectDTO,
    TaskDTO,
    LogDTO,
)
from backend.types.identifiers import UserId
from backend.services.auth_service import AuthService
from backend.services.pagination_service import PaginationService
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User, Task, Log, Project
from core.models.project_user import ProjectUser
from bd_core.database import Repository


class UserService:
    __slots__ = ("_auth_service", "_paginator")

    def __init__(
        self,
        auth_service: AuthService,
        paginator: PaginationService,
    ) -> None:
        self._auth_service = auth_service
        self._paginator = paginator

    async def create(
        self,
        data: UserCreateDTO,
        session: AsyncSession,
    ) -> Result[UserDTO, str]:
        from core.enums import Roles, SubscriptionTier, get_ocr_page_limit

        repo = Repository(session, User)

        existing = await repo.query(email=data.email)
        if existing:
            return Err(f"User with email '{data.email}' already exists")

        hashed_password = self._auth_service.hash_password(data.password)

        # Split full_name into name and last_name
        name_parts = data.full_name.split(" ", 1)
        name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        new_user = User(
            id=str(ULID()),
            email=data.email,
            password=hashed_password,
            name=name,
            last_name=last_name,
            subscription=SubscriptionTier.FREE.value,
            role_type=Roles.EDITOR.value,
            limit=get_ocr_page_limit(SubscriptionTier.FREE),
            permissions=data.permissions,
        )

        await repo.create(new_user)
        await session.commit()

        return Ok(UserDTO.model_validate(new_user.to_dict()))

    async def get_by_id(
        self,
        user_id: str,
        session: AsyncSession,
    ) -> Result[UserDTO, str]:
        repo = Repository(session, User)
        user = await repo.get(user_id)

        if not user:
            return Err(f"User with id '{user_id}' not found")

        return Ok(UserDTO.model_validate(user.to_dict()))

    async def get_by_email(
        self,
        email: str,
        session: AsyncSession,
    ) -> Result[UserDTO, str]:
        repo = Repository(session, User)
        users = await repo.query(email=email)

        if not users:
            return Err(f"User with email '{email}' not found")

        return Ok(UserDTO.model_validate(users[0].to_dict()))

    async def update(
        self,
        user_id: str,
        data: UserUpdateDTO,
        session: AsyncSession,
    ) -> Result[UserDTO, str]:
        repo = Repository(session, User)
        user = await repo.get(user_id)

        if not user:
            return Err(f"User with id '{user_id}' not found")

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                # Handle full_name -> name/last_name conversion
                if field == "full_name":
                    name_parts = value.split(" ", 1)
                    user.name = name_parts[0]
                    user.last_name = name_parts[1] if len(name_parts) > 1 else ""
                else:
                    setattr(user, field, value)

        await repo.update(user)
        await session.commit()

        return Ok(UserDTO.model_validate(user.to_dict()))

    async def delete(
        self,
        user_id: str,
        requesting_user_id: str,
        session: AsyncSession,
    ) -> Result[None, str]:
        if user_id == requesting_user_id:
            return Err("Cannot delete your own account")

        repo = Repository(session, User)
        user = await repo.get(user_id)

        if not user:
            return Err(f"User with id '{user_id}' not found")

        await repo.delete(user)
        await session.commit()

        return Ok(None)

    async def list_all(
        self,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[UserDTO]:
        repo = Repository(session, User)

        total = await repo.count(**filters)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        users = await repo.query(
            limit=meta.per_page,
            offset=(meta.current_page - 1) * meta.per_page,
            options=[User.tasks, User.projects],              **filters,
        )

        items = [UserDTO.model_validate(u.to_dict()) for u in users]

        return PaginatedResult(items=items, meta=meta)

    async def get_user_projects(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
    ) -> PaginatedResult[ProjectDTO]:
        assoc_repo = Repository(session, ProjectUser)
        project_repo = Repository(session, Project)

        associations = await assoc_repo.query(user_id=user_id)
        project_ids = [a.project_id for a in associations]

        total = len(project_ids)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        projects = await project_repo.query(
            in_={Project.id: project_ids},
            options=[Project.developers, Project.tasks],          )

        items = [ProjectDTO.model_validate(p.to_dict()) for p in projects]

        return PaginatedResult(items=items, meta=meta)

    async def get_user_tasks(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
    ) -> PaginatedResult[TaskDTO]:
        repo = Repository(session, Task)

        total = await repo.count(user_id=user_id)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        tasks = await repo.query(
            user_id=user_id,
            limit=meta.per_page,
            offset=(meta.current_page - 1) * meta.per_page,
            options=[Task.logs],
        )

        items = [TaskDTO.model_validate(t.to_dict()) for t in tasks]

        return PaginatedResult(items=items, meta=meta)

    async def get_user_logs(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
    ) -> PaginatedResult[LogDTO]:
        repo = Repository(session, Log)

        total = await repo.count(user_id=user_id)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        logs = await repo.query(
            user_id=user_id,
            limit=meta.per_page,
            offset=(meta.current_page - 1) * meta.per_page,
        )

        items = [LogDTO.model_validate(log.to_dict()) for log in logs]

        return PaginatedResult(items=items, meta=meta)
