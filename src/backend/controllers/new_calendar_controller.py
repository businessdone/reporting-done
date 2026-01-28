from typing import Sequence
from datetime import date, datetime
import calendar

from fastapi import Query, Depends, APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from backend.services import AvailabilityService
from backend.types.dtos import AvailabilityDTO
from backend.types.result import Err
from backend.protocols.session import ISession
from backend.dependencies import (
    get_session,
    get_current_user,
    is_admin,
    get_availability_service,
)
from core.models import User, OfficeAvailability
from core.models.project_user import ProjectUser
from database.repositories.repository import Repository


new_calendar_router = APIRouter(prefix="/calendar")


def can_view_calendar(current_user: User, target_user_id: str, session) -> bool:
    if current_user.id == target_user_id:
        return True
    if is_admin(current_user):
        return True
    
    project_user_repo = Repository(session, ProjectUser)
    current_user_projects = project_user_repo.query(user_id=current_user.id)
    current_project_ids = {pu.project_id for pu in current_user_projects}
    
    target_user_projects = project_user_repo.query(user_id=target_user_id)
    target_project_ids = {pu.project_id for pu in target_user_projects}
    
    return bool(current_project_ids & target_project_ids)


def can_edit_calendar(current_user: User, target_user_id: str) -> bool:
    if current_user.id == target_user_id:
        return True
    return is_admin(current_user)


class ViewableUserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    can_edit: bool


class DailyAvailabilityResponse(BaseModel):
    date: str
    status: str
    day_of_week: int


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    created_at: int
    status: str | None = None

    # Legacy field alias
    @property
    def timestamp(self) -> int:
        return self.created_at


class UserCalendarResponse(BaseModel):
    user_id: str
    user_name: str
    year: int
    month: int
    availability: Sequence[DailyAvailabilityResponse]
    tasks: Sequence[TaskResponse]
    can_edit: bool


class CalendarUpdateRequest(BaseModel):
    office_dates: Sequence[str]


class CalendarUpdateResponse(BaseModel):
    message: str
    user_id: str
    year: int
    month: int
    saved_office_days: int


@new_calendar_router.get("/viewable-users", response_model=Sequence[ViewableUserResponse])
def get_viewable_users_endpoint(
    session: ISession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    with session as s:
        user_repo = Repository(s, User)
        
        if is_admin(current_user):
            all_users = user_repo.query()
            return [
                ViewableUserResponse(
                    id=u.id,
                    full_name=u.full_name,
                    email=u.email,
                    can_edit=True,
                )
                for u in all_users
            ]
        
        project_user_repo = Repository(s, ProjectUser)
        current_user_project_memberships = project_user_repo.query(user_id=current_user.id)
        current_project_ids = {pu.project_id for pu in current_user_project_memberships}
        
        viewable_user_ids: set[str] = {current_user.id}
        for project_id in current_project_ids:
            project_members = project_user_repo.query(project_id=project_id)
            for pm in project_members:
                viewable_user_ids.add(pm.user_id)
        
        viewable_users = []
        for uid in viewable_user_ids:
            user = user_repo.get(uid)
            if user:
                viewable_users.append(
                    ViewableUserResponse(
                        id=user.id,
                        full_name=user.full_name,
                        email=user.email,
                        can_edit=(user.id == current_user.id),
                    )
                )
        
        return viewable_users


@new_calendar_router.get("/{user_id}", response_model=UserCalendarResponse)
def get_user_calendar_endpoint(
    user_id: str,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    session: ISession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    availability_service: AvailabilityService = Depends(get_availability_service),
):
    with session as s:
        if not can_view_calendar(current_user, user_id, s):
            raise HTTPException(status_code=403, detail="Not authorized to view this calendar")
    
    result = availability_service.get_user_availability(user_id, year, month, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=404, detail=result.error)
    
    dto = result.value
    
    from backend.services.task_service import TaskService
    from backend.dependencies.services import get_task_service
    from backend.types.pagination import PaginationParams
    
    task_service = get_task_service()
    tasks_result = task_service.list_for_user(
        user_id,
        PaginationParams(page=1, per_page=1000),
        session,
    )
    
    first_day = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last_day_dt = datetime(year, month, last_day, 23, 59, 59)

    month_tasks = [
        t for t in tasks_result.items
        if first_day <= t.created_at.replace(tzinfo=None) <= last_day_dt
    ]

    return UserCalendarResponse(
        user_id=dto.user_id,
        user_name=dto.user_name,
        year=dto.year,
        month=dto.month,
        availability=[
            DailyAvailabilityResponse(
                date=a.date.isoformat(),
                status=a.status,
                day_of_week=a.day_of_week,
            )
            for a in dto.availability
        ],
        tasks=[
            TaskResponse(
                id=t.id,
                title=t.title,
                description=t.description,
                created_at=int(t.created_at.timestamp()),
                status=t.status,
            )
            for t in month_tasks
        ],
        can_edit=can_edit_calendar(current_user, user_id),
    )


@new_calendar_router.post("/{user_id}", response_model=CalendarUpdateResponse)
def update_user_calendar_endpoint(
    user_id: str,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    payload: CalendarUpdateRequest = Body(...),
    session: ISession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    availability_service: AvailabilityService = Depends(get_availability_service),
):
    if not can_edit_calendar(current_user, user_id):
        raise HTTPException(status_code=403, detail="Not authorized to update this calendar")
    
    try:
        office_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in payload.office_dates]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    
    for d in office_dates:
        if d.year != year or d.month != month:
            raise HTTPException(
                status_code=400,
                detail=f"Date {d} is not in {year}-{month:02d}",
            )
    
    result = availability_service.batch_update_month(user_id, year, month, office_dates, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)
    
    return CalendarUpdateResponse(
        message="Calendar updated successfully",
        user_id=user_id,
        year=year,
        month=month,
        saved_office_days=len(office_dates),
    )
