from typing import Set, Dict, List, Optional
import calendar
from datetime import date, timedelta

from core.models import Task, User, OfficeAvailability
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.calendar_page import (
    PydanticBackendTask,
    PydanticBackendDailyAvailability,
    PydanticBackendUserCalendarResponse,
)
from businessdone_core.database import Repository


async def get_user_availability_data(
    session: AsyncSession, user_id: str, year: int, month: int
) -> PydanticBackendUserCalendarResponse:
    user_repo = Repository(session, User)
    user = await user_repo.get(user_id)
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    start_date = date(year, month, 1)
    num_days_in_month = calendar.monthrange(year, month)[1]
    end_date = date(year, month, num_days_in_month)

    office_availability_repo = Repository(session, OfficeAvailability)
    availability_entries: List[OfficeAvailability] = (
        await office_availability_repo.query(
            user_id=user_id,
            day__gte=start_date,
            day__lte=end_date,
        )
    )

    presence_map: Dict[date, bool] = {
        entry.day: entry.present for entry in availability_entries
    }

    daily_availability_models: List[PydanticBackendDailyAvailability] = []
    current_day = start_date
    while current_day <= end_date:
        is_present = presence_map.get(current_day, False)
        status_str = ""
        if current_day.weekday() >= 5:
            status_str = "Off"
        elif is_present:
            status_str = "Office"
        else:
            status_str = "Remote"

        daily_availability_models.append(
            PydanticBackendDailyAvailability(
                date=current_day.isoformat(),
                status=status_str,
                day_of_week=current_day.weekday(),
            )
        )
        current_day += timedelta(days=1)

    task_repo = Repository(session, Task)
    user_tasks_orm: List[Task] = await task_repo.query(user_id=user_id)

    task_response_models: List[PydanticBackendTask] = []
    for task_orm in user_tasks_orm:
        task_response_models.append(
            PydanticBackendTask(
                id=task_orm.id,
                title=task_orm.title,
                description=task_orm.description,
                created_at=int(task_orm.created_at.timestamp()),
                status=task_orm.status,
            )
        )

    return PydanticBackendUserCalendarResponse(
        user_id=user.id,
        user_name=user.full_name,
        year=year,
        month=month,
        availability=daily_availability_models,
        tasks=task_response_models,
    )


async def update_single_day_availability(
    session: AsyncSession,
    user_id: str,
    day_str: str,
    status: str,
) -> PydanticBackendDailyAvailability:
    user_repo = Repository(session, User)
    user = await user_repo.get(user_id)
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    try:
        target_date = date.fromisoformat(day_str)
    except ValueError:
        raise ValueError(f"Invalid date format: {day_str}. Use YYYY-MM-DD.")

    is_present: bool
    if target_date.weekday() >= 5:
        if status.lower() not in ["off", ""]:
            raise ValueError(
                f"Cannot set active work status ({status}) for a weekend day: {day_str}. Only 'Off' is allowed."
            )
        is_present = False
    else:
        if status.lower() == "office":
            is_present = True
        elif status.lower() == "remote":
            is_present = False
        elif status.lower() == "off":
            is_present = False
        else:
            raise ValueError(
                f"Invalid status: {status}. Must be 'Office', 'Remote', or 'Off'."
            )

    office_availability_repo = Repository(session, OfficeAvailability)
    existing_entries = await office_availability_repo.query(
        user_id=user_id,
        day=target_date,
    )
    availability_entry: Optional[OfficeAvailability] = (
        existing_entries[0] if existing_entries else None
    )

    final_status_str = status

    if target_date.weekday() >= 5:
        final_status_str = "Off"
        if availability_entry:
            availability_entry.present = False
    else:
        if availability_entry:
            availability_entry.present = is_present
        else:
            availability_entry = OfficeAvailability(
                user_id=user_id, day=target_date, present=is_present
            )
            await office_availability_repo.create(availability_entry)

        if is_present:
            final_status_str = "Office"
        else:
            final_status_str = "Remote"
            if status.lower() == "off":
                final_status_str = "Off"

    await session.commit()

    if (
        not availability_entry
        and target_date.weekday() >= 5
        and status.lower() == "off"
    ):
        response_date = target_date
        response_status = "Off"
    elif availability_entry:
        response_date = availability_entry.day
        response_status = final_status_str
    else:
        raise Exception(
            "Availability entry not found or created unexpectedly."
        )

    return PydanticBackendDailyAvailability(
        date=response_date.isoformat(),
        status=response_status,
        day_of_week=response_date.weekday(),
    )


async def batch_update_monthly_availability(
    session: AsyncSession,
    user_id: str,
    year: int,
    month: int,
    office_dates: List[str],
) -> PydanticBackendUserCalendarResponse:
    user_repo = Repository(session, User)
    user = await user_repo.get(user_id)
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    office_availability_repo = Repository(session, OfficeAvailability)
    parsed_office_dates: Set[date] = {
        date.fromisoformat(d_str) for d_str in office_dates
    }

    start_date = date(year, month, 1)
    num_days_in_month = calendar.monthrange(year, month)[1]
    end_date = date(year, month, num_days_in_month)

    existing_entries_list: List[OfficeAvailability] = (
        await office_availability_repo.query(
            user_id=user_id,
            day__gte=start_date,
            day__lte=end_date,
        )
    )

    existing_entries_map: Dict[date, OfficeAvailability] = {
        e.day: e for e in existing_entries_list
    }

    current_processing_day = start_date
    while current_processing_day <= end_date:
        if current_processing_day.weekday() >= 5:
            if current_processing_day in existing_entries_map:
                existing_entries_map[current_processing_day].present = False
            current_processing_day += timedelta(days=1)
            continue

        is_present_for_day = current_processing_day in parsed_office_dates

        entry = existing_entries_map.get(current_processing_day)
        if entry:
            entry.present = is_present_for_day
        else:
            new_entry = OfficeAvailability(
                user_id=user_id,
                day=current_processing_day,
                present=is_present_for_day,
            )
            await office_availability_repo.create(new_entry)

        current_processing_day += timedelta(days=1)

    await session.commit()

    return await get_user_availability_data(session, user_id, year, month)
