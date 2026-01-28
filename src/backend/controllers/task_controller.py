from io import StringIO
import csv
from typing import Any, Sequence

from fastapi import Query, Depends, APIRouter, HTTPException
from pydantic import Field, BaseModel
from fastapi.responses import StreamingResponse

from backend.services import TaskService
from core.models import User
from backend.types.dtos import LogDTO, TaskDTO, TaskCreateDTO, TaskUpdateDTO
from backend.dependencies import (
    is_admin,
    get_session,
    require_admin,
    get_current_user,
    get_task_service,
)
from backend.types.result import Err
from backend.types.pagination import PaginationParams
from sqlalchemy.ext.asyncio import AsyncSession

task_router = APIRouter(prefix="/task")


class TaskCreateRequest(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=500)
    hours_required: float = Field(ge=0)
    description: str = Field(max_length=10000)
    status: str | None = None
    user_id: str | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    hours_required: float | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=10000)
    status: str | None = None
    user_id: str | None = None
    returned: bool | None = None


class PaginatedTasksResponse(BaseModel):
    items: Sequence[TaskDTO]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class PaginatedLogsResponse(BaseModel):
    items: Sequence[LogDTO]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


@task_router.post("/", response_model=TaskDTO)
async def create_task_endpoint(
    body: TaskCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
):
    assigned_user_id = body.user_id

    if (
        assigned_user_id
        and assigned_user_id != str(current_user.id)
        and not is_admin(current_user)
    ):
        assigned_user_id = str(current_user.id)

    dto = TaskCreateDTO(
        project_id=body.project_id,
        title=body.title,
        hours_required=body.hours_required,
        description=body.description,
        status=body.status,
        user_id=assigned_user_id,
    )

    result = await task_service.create(dto, str(current_user.id), session)

    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)

    return result.value


@task_router.get("/", response_model=PaginatedTasksResponse)
async def get_all_tasks_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    sort: str | None = Query(None),
    order: str = Query("desc"),
    status: str | None = Query(None),
    project_id: str | None = Query(None),
    user_id: str | None = Query(None),
    returned: bool | None = Query(None),
    date_from: int | None = Query(
        None, description="Unix timestamp for start date"
    ),
    date_to: int | None = Query(
        None, description="Unix timestamp for end date"
    ),
    hours_progress: str | None = Query(
        None,
        description="Filter by hours progress: overdue, on_track, not_started",
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
):
    pagination = PaginationParams(
        page=page,
        per_page=limit,
        sort_by=sort,
        sort_order=order,
    )

    filters: dict[str, Any] = {}
    if status:
        filters["status"] = status
    if project_id:
        filters["project_id"] = project_id
    if user_id:
        filters["user_id"] = user_id
    if returned is not None:
        filters["returned"] = returned
    if date_from is not None:
        filters["created_at__gte"] = date_from
    if date_to is not None:
        filters["created_at__lte"] = date_to

    if is_admin(current_user):
        result = await task_service.list_all(pagination, session, **filters)
    else:
        result = await task_service.list_for_user(
            str(current_user.id), pagination, session, **filters
        )

    if hours_progress:
        filtered_items = []
        for task in result.items:
            if (
                hours_progress == "overdue"
                and task.hours_worked > task.hours_required
            ):
                filtered_items.append(task)
            elif (
                hours_progress == "on_track"
                and 0 < task.hours_worked <= task.hours_required
            ):
                filtered_items.append(task)
            elif hours_progress == "not_started" and task.hours_worked == 0:
                filtered_items.append(task)
        return PaginatedTasksResponse(
            items=filtered_items,
            total=len(filtered_items),
            page=result.page,
            per_page=result.meta.per_page,
            has_next=False,
            has_prev=result.has_prev,
        )

    return PaginatedTasksResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@task_router.get("/export", response_class=StreamingResponse)
async def export_tasks_csv(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    task_service: TaskService = Depends(get_task_service),
):
    pagination = PaginationParams(page=1, per_page=10000)
    result = await task_service.list_all(pagination, session)

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "ID",
            "Title",
            "User",
            "Project",
            "Status",
            "Hours Required",
            "Hours Worked",
            "Date",
        ]
    )

    for task in result.items:
        writer.writerow(
            [
                task.id,
                task.title,
                task.user_name,
                task.project_name,
                task.status or "",
                task.hours_required,
                task.hours_worked,
                task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tasks.csv"},
    )


@task_router.get("/{task_id}", response_model=TaskDTO)
async def get_task_endpoint(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
):
    result = await task_service.get_by_id(task_id, session)

    if isinstance(result, Err):
        raise HTTPException(status_code=404, detail=result.error)

    task = result.value

    if not is_admin(current_user) and task.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access forbidden")

    return task


@task_router.put("/{task_id}", response_model=TaskDTO)
async def update_task_endpoint(
    task_id: str,
    body: TaskUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
):
    dto = TaskUpdateDTO(
        title=body.title,
        hours_required=body.hours_required,
        description=body.description,
        status=body.status,
        user_id=body.user_id,
        returned=body.returned,
    )

    result = await task_service.update(
        task_id,
        dto,
        str(current_user.id),
        is_admin(current_user),
        session,
    )

    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)

    return result.value


@task_router.delete("/{task_id}", status_code=204)
async def delete_task_endpoint(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
    task_service: TaskService = Depends(get_task_service),
):
    result = await task_service.delete(task_id, session)

    if isinstance(result, Err):
        raise HTTPException(status_code=404, detail=result.error)


@task_router.get("/{task_id}/logs", response_model=PaginatedLogsResponse)
async def get_task_logs_endpoint(
    task_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
):
    pagination = PaginationParams(page=page, per_page=limit)
    result = await task_service.get_task_logs(task_id, pagination, session)

    return PaginatedLogsResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@task_router.get(
    "/project/{project_id}", response_model=PaginatedTasksResponse
)
async def get_tasks_by_project_endpoint(
    project_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
):
    pagination = PaginationParams(page=page, per_page=limit)
    result = await task_service.list_all(pagination, session, project_id=project_id)

    return PaginatedTasksResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@task_router.get("/user/{user_id}", response_model=PaginatedTasksResponse)
async def get_tasks_by_user_endpoint(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
):
    if str(current_user.id) != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access forbidden")

    pagination = PaginationParams(page=page, per_page=limit)
    result = await task_service.list_for_user(user_id, pagination, session)

    return PaginatedTasksResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )
