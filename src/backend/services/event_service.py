from typing import Any
from datetime import datetime

from ulid import ULID

from backend.types.result import Result, Ok, Err
from backend.types.pagination import PaginationParams, PaginatedResult
from backend.types.dtos import EventCreateDTO, EventUpdateDTO, EventDTO
from backend.services.pagination_service import PaginationService
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import Event
from businessdone_core.database import Repository


class EventService:
    __slots__ = ("_paginator",)

    def __init__(self, paginator: PaginationService) -> None:
        self._paginator = paginator

    async def create(
        self,
        data: EventCreateDTO,
        user_id: str,
        session: AsyncSession,
    ) -> Result[EventDTO, str]:
        repo = Repository(session, Event)

        try:
            event_date_ts = int(datetime.strptime(data.event_date, "%Y-%m-%d").timestamp())
        except ValueError:
            return Err("Invalid date format. Use YYYY-MM-DD")

        new_event = Event(
            id=str(ULID()),
            user_id=user_id,
            title=data.title,
            description=data.description,
            event_type=data.event_type,
            event_date=event_date_ts,
            start_time=data.start_time,
            end_time=data.end_time,
            created_at=int(datetime.now().timestamp()),
        )

        await repo.create(new_event)
        await session.commit()

        return Ok(EventDTO.model_validate(new_event.to_dict()))

    async def get_by_id(
        self,
        event_id: str,
        session: AsyncSession,
    ) -> Result[EventDTO, str]:
        repo = Repository(session, Event)
        event = await repo.get(event_id)

        if not event:
            return Err(f"Event with id '{event_id}' not found")

        return Ok(EventDTO.model_validate(event.to_dict()))

    async def update(
        self,
        event_id: str,
        data: EventUpdateDTO,
        user_id: str,
        is_admin: bool,
        session: AsyncSession,
    ) -> Result[EventDTO, str]:
        repo = Repository(session, Event)
        event = await repo.get(event_id)

        if not event:
            return Err(f"Event with id '{event_id}' not found")

        if not is_admin and event.user_id != user_id:
            return Err("Not authorized to update this event")

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                if field == "event_date":
                    try:
                        value = int(datetime.strptime(value, "%Y-%m-%d").timestamp())
                    except ValueError:
                        return Err("Invalid date format. Use YYYY-MM-DD")
                setattr(event, field, value)

        await session.commit()

        updated = await repo.get(event_id)
        if not updated:
            return Err(f"Event with id '{event_id}' not found after update")

        return Ok(EventDTO.model_validate(updated.to_dict()))

    async def delete(
        self,
        event_id: str,
        user_id: str,
        is_admin: bool,
        session: AsyncSession,
    ) -> Result[None, str]:
        repo = Repository(session, Event)
        event = await repo.get(event_id)

        if not event:
            return Err(f"Event with id '{event_id}' not found")

        if not is_admin and event.user_id != user_id:
            return Err("Not authorized to delete this event")

        await repo.delete(event)
        await session.commit()

        return Ok(None)

    async def list_all(
        self,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[EventDTO]:
        repo = Repository(session, Event)

        total = await repo.count(**filters)
        meta = self._paginator.calculate(total, pagination)

        if total == 0:
            return PaginatedResult(items=[], meta=meta)

        events = await repo.query(
            limit=meta.per_page,
            offset=(meta.current_page - 1) * meta.per_page,
            **filters,
        )

        items = [EventDTO.model_validate(e.to_dict()) for e in events]

        return PaginatedResult(items=items, meta=meta)

    async def list_for_user(
        self,
        user_id: str,
        pagination: PaginationParams,
        session: AsyncSession,
        **filters: Any,
    ) -> PaginatedResult[EventDTO]:
        combined_filters = {**filters, "user_id": user_id}
        return await self.list_all(pagination, session, **combined_filters)

    async def get_user_events_for_month(
        self,
        user_id: str,
        year: int,
        month: int,
        session: AsyncSession,
    ) -> list[EventDTO]:
        repo = Repository(session, Event)

        from calendar import monthrange
        first_day_ts = int(datetime(year, month, 1).timestamp())
        last_day = monthrange(year, month)[1]
        last_day_ts = int(datetime(year, month, last_day, 23, 59, 59).timestamp())

        all_events = await repo.query(user_id=user_id)

        month_events = [
            e for e in all_events
            if first_day_ts <= e.event_date <= last_day_ts
        ]

        return [EventDTO.model_validate(e.to_dict()) for e in month_events]
