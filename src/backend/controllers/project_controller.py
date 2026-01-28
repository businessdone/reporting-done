from typing import Sequence, Any

from fastapi import Query, Depends, APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend.services import ProjectService
from backend.types.dtos import ProjectDTO, ProjectCreateDTO, ProjectUpdateDTO, UserDTO, TaskDTO
from backend.types.pagination import PaginationParams
from backend.types.result import Err
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dependencies import (
    get_session,
    get_current_user,
    require_admin,
    is_admin,
    get_project_service,
)
from core.models import User


project_router = APIRouter(prefix="/project")


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    send_email: bool = False
    archived: bool = False


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    send_email: bool | None = None
    archived: bool | None = None


class AssignUserRequest(BaseModel):
    user_id: str


class PaginatedResponse(BaseModel):
    items: Sequence[ProjectDTO] | Sequence[UserDTO] | Sequence[TaskDTO]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


@project_router.post("/", response_model=ProjectDTO)
async def create_project_endpoint(
    body: ProjectCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    project_service: ProjectService = Depends(get_project_service),
):
    dto = ProjectCreateDTO(
        name=body.name,
        email=body.email,
        send_email=body.send_email,
        archived=body.archived,
    )
    
    result = project_service.create(dto, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)
    
    return result.value


@project_router.get("/", response_model=PaginatedResponse)
def get_all_projects_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    sort: str | None = Query(None),
    order: str = Query("asc"),
    archived: bool | None = Query(None),
    send_email: bool | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
):
    pagination = PaginationParams(
        page=page,
        per_page=limit,
        sort_by=sort,
        sort_order=order,
    )
    
    filters: dict[str, Any] = {}
    if archived is not None:
        filters["archived"] = archived
    if send_email is not None:
        filters["send_email"] = send_email
    
    if is_admin(current_user):
        result = project_service.list_all(pagination, session, **filters)
    else:
        result = project_service.list_for_user(current_user.id, pagination, session, **filters)
    
    return PaginatedResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@project_router.get("/{project_id}", response_model=ProjectDTO)
def get_project_endpoint(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
):
    result = project_service.get_by_id(project_id, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=404, detail=result.error)
    
    project = result.value
    
    if not is_admin(current_user):
        user_projects = project_service.list_for_user(
            current_user.id,
            PaginationParams(page=1, per_page=1000),
            session,
        )
        project_ids = [p.id for p in user_projects.items]
        
        if project_id not in project_ids:
            raise HTTPException(status_code=403, detail="Access forbidden")
    
    return project


@project_router.put("/{project_id}", response_model=ProjectDTO)
async def update_project_endpoint(
    project_id: str,
    body: ProjectUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    project_service: ProjectService = Depends(get_project_service),
):
    dto = ProjectUpdateDTO(
        name=body.name,
        email=body.email,
        send_email=body.send_email,
        archived=body.archived,
    )
    
    result = project_service.update(project_id, dto, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=404, detail=result.error)
    
    return result.value


@project_router.delete("/{project_id}", status_code=204)
async def delete_project_endpoint(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    project_service: ProjectService = Depends(get_project_service),
):
    result = project_service.delete(project_id, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)


@project_router.post("/{project_id}/assign", response_model=ProjectDTO)
def assign_user_endpoint(
    project_id: str,
    body: AssignUserRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    project_service: ProjectService = Depends(get_project_service),
):
    result = project_service.assign_user(project_id, body.user_id, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)
    
    return result.value


@project_router.post("/{project_id}/remove_user", response_model=ProjectDTO)
def remove_user_endpoint(
    project_id: str,
    body: AssignUserRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    project_service: ProjectService = Depends(get_project_service),
):
    result = project_service.remove_user(project_id, body.user_id, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)
    
    return result.value


@project_router.get("/{project_id}/users", response_model=PaginatedResponse)
def get_project_users_endpoint(
    project_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
):
    pagination = PaginationParams(page=page, per_page=limit)
    result = project_service.get_project_users(project_id, pagination, session)
    
    return PaginatedResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@project_router.get("/{project_id}/tasks", response_model=PaginatedResponse)
def get_project_tasks_endpoint(
    project_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
):
    pagination = PaginationParams(page=page, per_page=limit)
    result = project_service.get_project_tasks(project_id, pagination, session)
    
    return PaginatedResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )
