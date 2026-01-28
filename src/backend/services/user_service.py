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
from database.interfaces.session import ISession
from core.models.user import User
from core.models.task import Task
from core.models.log import Log
from core.models.project import Project
from core.models.project_user import ProjectUser
from database.repositories.repository import Repository


class UserService:
    __slots__ = ("_auth_service", "_paginator")
    
    def __init__(
        self,
        auth_service: AuthService,
        paginator: PaginationService,
    ) -> None:
        self._auth_service = auth_service
        self._paginator = paginator
    
    def create(
        self,
        data: UserCreateDTO,
        session: ISession,
    ) -> Result[UserDTO, str]:
        from core.enums import Roles, SubscriptionTier, get_ocr_page_limit

        with session as s:
            repo = Repository(s, User)

            existing = repo.query(email=data.email)
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
                projects=[],
                tasks=[],
            )

            repo.create(new_user)

            return Ok(UserDTO.model_validate(new_user.to_dict()))
    
    def get_by_id(
        self,
        user_id: str,
        session: ISession,
    ) -> Result[UserDTO, str]:
        with session as s:
            repo = Repository(s, User)
            user = repo.get(user_id)
            
            if not user:
                return Err(f"User with id '{user_id}' not found")
            
            return Ok(UserDTO.model_validate(user.to_dict()))
    
    def get_by_email(
        self,
        email: str,
        session: ISession,
    ) -> Result[UserDTO, str]:
        with session as s:
            repo = Repository(s, User)
            users = repo.query(email=email)
            
            if not users:
                return Err(f"User with email '{email}' not found")
            
            return Ok(UserDTO.model_validate(users[0].to_dict()))
    
    def update(
        self,
        user_id: str,
        data: UserUpdateDTO,
        session: ISession,
    ) -> Result[UserDTO, str]:
        with session as s:
            repo = Repository(s, User)
            user = repo.get(user_id)

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
            
            repo.update(user)
            
            return Ok(UserDTO.model_validate(user.to_dict()))
    
    def delete(
        self,
        user_id: str,
        requesting_user_id: str,
        session: ISession,
    ) -> Result[None, str]:
        if user_id == requesting_user_id:
            return Err("Cannot delete your own account")
        
        with session as s:
            repo = Repository(s, User)
            user = repo.get(user_id)
            
            if not user:
                return Err(f"User with id '{user_id}' not found")
            
            repo.delete(user)
            s.commit()
            
            return Ok(None)
    
    def list_all(
        self,
        pagination: PaginationParams,
        session: ISession,
        **filters: Any,
    ) -> PaginatedResult[UserDTO]:
        with session as s:
            repo = Repository(s, User)
            
            total = repo.count(**filters)
            meta = self._paginator.calculate(total, pagination)
            
            if total == 0:
                return PaginatedResult(items=[], meta=meta)
            
            users = repo.query(
                limit=meta.per_page,
                offset=(meta.current_page - 1) * meta.per_page,
                options=[User.tasks, User.projects],
                **filters,
            )
            
            items = [UserDTO.model_validate(u.to_dict()) for u in users]
            
            return PaginatedResult(items=items, meta=meta)
    
    def get_user_projects(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: ISession,
    ) -> PaginatedResult[ProjectDTO]:
        with session as s:
            assoc_repo = Repository(s, ProjectUser)
            project_repo = Repository(s, Project)
            
            associations = assoc_repo.query(user_id=user_id)
            project_ids = [a.project_id for a in associations]
            
            total = len(project_ids)
            meta = self._paginator.calculate(total, pagination)
            
            if total == 0:
                return PaginatedResult(items=[], meta=meta)
            
            projects = project_repo.query(
                in_={Project.id: project_ids},
                options=[Project.developers, Project.tasks],
            )
            
            items = [ProjectDTO.model_validate(p.to_dict()) for p in projects]
            
            return PaginatedResult(items=items, meta=meta)
    
    def get_user_tasks(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: ISession,
    ) -> PaginatedResult[TaskDTO]:
        with session as s:
            repo = Repository(s, Task)
            
            total = repo.count(user_id=user_id)
            meta = self._paginator.calculate(total, pagination)
            
            if total == 0:
                return PaginatedResult(items=[], meta=meta)
            
            tasks = repo.query(
                user_id=user_id,
                limit=meta.per_page,
                offset=(meta.current_page - 1) * meta.per_page,
                options=[Task.logs],
            )
            
            items = [TaskDTO.model_validate(t.to_dict()) for t in tasks]
            
            return PaginatedResult(items=items, meta=meta)
    
    def get_user_logs(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: ISession,
    ) -> PaginatedResult[LogDTO]:
        with session as s:
            repo = Repository(s, Log)
            
            total = repo.count(user_id=user_id)
            meta = self._paginator.calculate(total, pagination)
            
            if total == 0:
                return PaginatedResult(items=[], meta=meta)
            
            logs = repo.query(
                user_id=user_id,
                limit=meta.per_page,
                offset=(meta.current_page - 1) * meta.per_page,
            )
            
            items = [LogDTO.model_validate(log.to_dict()) for log in logs]
            
            return PaginatedResult(items=items, meta=meta)

