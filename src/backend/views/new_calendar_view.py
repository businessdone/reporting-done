from typing import List
import calendar
from datetime import date, datetime, timedelta

from core.models import Task, User, OfficeAvailability
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.calendar_page import (
    PydanticBackendTask,
    PydanticBackendDailyAvailability,
    PydanticBackendUserCalendarResponse,
)
from bd_core.database import Repository


async def get_new_calendar_data_for_user(
    session: AsyncSession,
    user_id: str,
    year: int,
    month: int,
) -> PydanticBackendUserCalendarResponse:
    user_repo = Repository(session, User)
    user = await user_repo.get(user_id)
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    availability_list: List[PydanticBackendDailyAvailability] = []
    month_start_date = date(year, month, 1)
    num_days_in_month = calendar.monthrange(year, month)[1]
    month_end_date = date(year, month, num_days_in_month)

    office_availability_repo = Repository(session, OfficeAvailability)
    db_availabilities: List[OfficeAvailability] = await office_availability_repo.query(
        user_id=user_id,
        day__gte=month_start_date,
        day__lte=month_end_date,
    )

    db_presence_map: dict[date, bool] = {
        avail.day: avail.present for avail in db_availabilities
    }

    current_iter_date = month_start_date
    while current_iter_date <= month_end_date:
        is_present = db_presence_map.get(current_iter_date, False)
        status_str = ""
        day_of_week = current_iter_date.weekday()

        if day_of_week >= 5:
            status_str = "Off"
        elif is_present:
            status_str = "Office"
        else:
            status_str = "Remote"

        availability_list.append(
            PydanticBackendDailyAvailability(
                date=current_iter_date.isoformat(),
                status=status_str,
                day_of_week=day_of_week,
            )
        )
        current_iter_date += timedelta(days=1)

    task_list: List[PydanticBackendTask] = []
    task_repo = Repository(session, Task)
    start_date = datetime(year, month, 1, 0, 0, 0)
    end_date = datetime(year, month, num_days_in_month, 23, 59, 59)
    user_tasks: List[Task] = await task_repo.query(
        user_id=user_id,
        created_at__gte=start_date,
        created_at__lte=end_date,
    )

    for task_item in user_tasks:
        unix_timestamp = int(task_item.created_at.timestamp())

        task_list.append(
            PydanticBackendTask(
                id=task_item.id,
                title=task_item.title,
                description=task_item.description,
                created_at=unix_timestamp,
                status=task_item.status,
            )
        )

    return PydanticBackendUserCalendarResponse(
        user_id=str(user.id),
        user_name=user.full_name,
        year=year,
        month=month,
        availability=availability_list,
        tasks=task_list,
    )
