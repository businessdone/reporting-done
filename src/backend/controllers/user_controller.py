from typing import Sequence

from fastapi import Query, Depends, Request, APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend.services import UserService
from backend.types.dtos import UserDTO, UserCreateDTO, UserUpdateDTO, ProjectDTO, TaskDTO, LogDTO
from backend.types.pagination import PaginationParams
from backend.types.result import Err
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dependencies import (
    get_session,
    get_current_user,
    require_admin,
    is_admin,
    get_user_service,
)
from core.models import User


user_router = APIRouter(prefix="/user")


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)
    permissions: int = Field(ge=0)


class UserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    permissions: int | None = Field(default=None, ge=0)


class PaginatedResponse(BaseModel):
    items: Sequence[UserDTO] | Sequence[ProjectDTO] | Sequence[TaskDTO] | Sequence[LogDTO]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class IsAdminResponse(BaseModel):
    is_admin: bool


@user_router.post("/", response_model=UserDTO)
async def create_user_endpoint(
    body: UserCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
):
    dto = UserCreateDTO(
        email=body.email,
        full_name=body.full_name,
        password=body.password,
        permissions=body.permissions,
    )
    
    result = user_service.create(dto, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)
    
    return result.value


@user_router.get("/is_admin", response_model=IsAdminResponse)
def is_admin_endpoint(
    current_user: User = Depends(get_current_user),
):
    return IsAdminResponse(is_admin=is_admin(current_user))


@user_router.get("/me", response_model=UserDTO)
async def get_current_user_details(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    result = user_service.get_by_id(current_user.id, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=404, detail=result.error)
    
    return result.value


@user_router.get("/", response_model=PaginatedResponse)
def get_all_users_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    sort: str | None = Query(None),
    order: str = Query("asc"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
):
    pagination = PaginationParams(
        page=page,
        per_page=limit,
        sort_by=sort,
        sort_order=order,
    )
    
    result = user_service.list_all(pagination, session)
    
    return PaginatedResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@user_router.get("/{user_id}", response_model=UserDTO)
def get_user_endpoint(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    if current_user.id != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to view this profile")
    
    result = user_service.get_by_id(user_id, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=404, detail=result.error)
    
    return result.value


@user_router.put("/{user_id}", response_model=UserDTO)
def update_user_endpoint(
    user_id: str,
    body: UserUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    if current_user.id != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to update this profile")
    
    dto = UserUpdateDTO(
        email=body.email,
        full_name=body.full_name,
        permissions=body.permissions if is_admin(current_user) else None,
    )
    
    result = user_service.update(user_id, dto, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=404, detail=result.error)
    
    return result.value


@user_router.delete("/{user_id}", status_code=204)
async def delete_user_endpoint(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
):
    result = user_service.delete(user_id, current_user.id, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)


@user_router.get("/{user_id}/projects", response_model=PaginatedResponse)
def get_user_projects_endpoint(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    if current_user.id != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    pagination = PaginationParams(page=page, per_page=limit)
    result = user_service.get_user_projects(user_id, pagination, session)
    
    return PaginatedResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@user_router.get("/{user_id}/tasks")
def get_user_tasks_endpoint(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    if current_user.id != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    pagination = PaginationParams(page=page, per_page=limit)
    result = user_service.get_user_tasks(user_id, pagination, session)
    
    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "per_page": result.meta.per_page,
        "has_next": result.has_next,
        "has_prev": result.has_prev,
    }


@user_router.get("/{user_id}/logs")
def get_user_logs_endpoint(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    if current_user.id != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    pagination = PaginationParams(page=page, per_page=limit)
    result = user_service.get_user_logs(user_id, pagination, session)
    
    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "per_page": result.meta.per_page,
        "has_next": result.has_next,
        "has_prev": result.has_prev,
    }
