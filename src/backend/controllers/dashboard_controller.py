from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import ProjectService, TaskService, LogService
from backend.types.pagination import PaginationParams
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dependencies import (
    get_session,
    get_current_user,
    is_admin,
    get_project_service,
    get_task_service,
    get_log_service,
)
from core.models import User
from core.enums.task_status import TaskStatus


dashboard_router = APIRouter()


class DashboardSummaryResponse(BaseModel):
    active_projects_count: int
    pending_tasks_count: int
    recent_logs_count: int
    is_admin_user: bool


@dashboard_router.get("/api/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    task_service: TaskService = Depends(get_task_service),
    log_service: LogService = Depends(get_log_service),
):
    user_is_admin = is_admin(current_user)
    no_limit_pagination = PaginationParams(page=1, per_page=10000)

    # NOTE: project_service is not yet async - will be converted in a future task
    if user_is_admin:
        projects_result = project_service.list_all(
            no_limit_pagination,
            session,
            archived=False,
        )
        active_projects_count = projects_result.total
    else:
        projects_result = project_service.list_for_user(
            current_user.id,
            no_limit_pagination,
            session,
            archived=False,
        )
        active_projects_count = sum(1 for p in projects_result.items if not p.archived)

    done_statuses = {TaskStatus.DONE.value, TaskStatus.CANCELLED.value}

    # TaskService is now async
    if user_is_admin:
        tasks_result = await task_service.list_all(no_limit_pagination, session)
    else:
        tasks_result = await task_service.list_for_user(
            current_user.id,
            no_limit_pagination,
            session,
        )

    pending_tasks_count = sum(
        1 for t in tasks_result.items
        if t.status and t.status not in done_statuses
    )

    # NOTE: log_service is not yet async - will be converted in a future task
    if user_is_admin:
        logs_result = log_service.list_all(no_limit_pagination, session)
    else:
        logs_result = log_service.list_for_user(
            current_user.id,
            no_limit_pagination,
            session,
        )

    recent_logs_count = logs_result.total

    return DashboardSummaryResponse(
        active_projects_count=active_projects_count,
        pending_tasks_count=pending_tasks_count,
        recent_logs_count=recent_logs_count,
        is_admin_user=user_is_admin,
    )
