from typing import Sequence

from fastapi import Query, Depends, APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.event_service import EventService
from backend.services.pagination_service import PaginationService
from backend.types.dtos import EventDTO, EventCreateDTO, EventUpdateDTO
from backend.types.pagination import PaginationParams
from backend.types.result import Err
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dependencies import (
    get_session,
    get_current_user,
    is_admin,
)
from core.models import User
from core.models.project_user import ProjectUser
from businessdone_core.database import Repository


event_router = APIRouter(prefix="/event")


async def can_view_user_events(current_user: User, target_user_id: str, session: AsyncSession) -> bool:
    if current_user.id == target_user_id:
        return True
    if is_admin(current_user):
        return True

    project_user_repo = Repository(session, ProjectUser)
    current_user_projects = await project_user_repo.query(user_id=current_user.id)
    current_project_ids = {pu.project_id for pu in current_user_projects}

    target_user_projects = await project_user_repo.query(user_id=target_user_id)
    target_project_ids = {pu.project_id for pu in target_user_projects}

    return bool(current_project_ids & target_project_ids)

_event_service = EventService(PaginationService())


class EventCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    event_type: str = Field(min_length=1, max_length=50)
    event_date: str
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


class EventUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    event_type: str | None = Field(default=None, min_length=1, max_length=50)
    event_date: str | None = None
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


class PaginatedEventResponse(BaseModel):
    items: Sequence[EventDTO]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


@event_router.post("/", response_model=EventDTO)
async def create_event_endpoint(
    body: EventCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    dto = EventCreateDTO(
        title=body.title,
        description=body.description,
        event_type=body.event_type,
        event_date=body.event_date,
        start_time=body.start_time,
        end_time=body.end_time,
    )

    result = await _event_service.create(dto, current_user.id, session)

    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)

    return result.value


@event_router.get("/", response_model=PaginatedEventResponse)
async def get_all_events_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    event_type: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pagination = PaginationParams(page=page, per_page=limit)

    filters = {}
    if event_type:
        filters["event_type"] = event_type

    if is_admin(current_user):
        result = await _event_service.list_all(pagination, session, **filters)
    else:
        result = await _event_service.list_for_user(current_user.id, pagination, session, **filters)

    return PaginatedEventResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@event_router.get("/my", response_model=PaginatedEventResponse)
async def get_my_events_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pagination = PaginationParams(page=page, per_page=limit)

    if year and month:
        events = await _event_service.get_user_events_for_month(
            current_user.id, year, month, session
        )
        return PaginatedEventResponse(
            items=events,
            total=len(events),
            page=1,
            per_page=len(events) or 25,
            has_next=False,
            has_prev=False,
        )

    result = await _event_service.list_for_user(current_user.id, pagination, session)

    return PaginatedEventResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@event_router.get("/user/{user_id}", response_model=PaginatedEventResponse)
async def get_user_events_endpoint(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not await can_view_user_events(current_user, user_id, session):
        raise HTTPException(status_code=403, detail="Not authorized to view this user's events")

    pagination = PaginationParams(page=page, per_page=limit)

    if year and month:
        events = await _event_service.get_user_events_for_month(user_id, year, month, session)
        return PaginatedEventResponse(
            items=events,
            total=len(events),
            page=1,
            per_page=len(events) or 25,
            has_next=False,
            has_prev=False,
        )

    result = await _event_service.list_for_user(user_id, pagination, session)

    return PaginatedEventResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.meta.per_page,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@event_router.get("/{event_id}", response_model=EventDTO)
async def get_event_endpoint(
    event_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await _event_service.get_by_id(event_id, session)

    if isinstance(result, Err):
        raise HTTPException(status_code=404, detail=result.error)

    event = result.value

    if not is_admin(current_user) and event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this event")

    return event


@event_router.put("/{event_id}", response_model=EventDTO)
async def update_event_endpoint(
    event_id: str,
    body: EventUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    dto = EventUpdateDTO(
        title=body.title,
        description=body.description,
        event_type=body.event_type,
        event_date=body.event_date,
        start_time=body.start_time,
        end_time=body.end_time,
    )

    result = await _event_service.update(
        event_id,
        dto,
        current_user.id,
        is_admin(current_user),
        session,
    )

    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)

    return result.value


@event_router.delete("/{event_id}", status_code=204)
async def delete_event_endpoint(
    event_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await _event_service.delete(
        event_id,
        current_user.id,
        is_admin(current_user),
        session,
    )

    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)
