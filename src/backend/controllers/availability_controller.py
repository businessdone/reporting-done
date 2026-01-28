from typing import Sequence
from datetime import date, datetime

from fastapi import Query, Depends, APIRouter, HTTPException, File, UploadFile, Body
from pydantic import BaseModel, Field

from backend.services import AvailabilityService
from backend.types.dtos import UserDTO
from backend.types.result import Err
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dependencies import (
    get_session,
    get_current_user,
    require_admin,
    is_admin,
    get_availability_service,
)
from backend.utils.xlsx_parser import FileParser, IFileParser
from core.models import User, OfficeAvailability
from bd_core.database import Repository


availability_router = APIRouter(prefix="/availability")


class UpdateDayRequest(BaseModel):
    date: str
    status: str


class BatchUpdateRequest(BaseModel):
    office_dates: Sequence[str]


class DailyAvailabilityResponse(BaseModel):
    date: date
    status: str
    day_of_week: int


class MonthlyAvailabilityResponse(BaseModel):
    user_id: str
    user_name: str
    year: int
    month: int
    availability: Sequence[DailyAvailabilityResponse]
    office_days_count: int


class UsersInOfficeResponse(BaseModel):
    date: date
    users: Sequence[UserDTO]
    total: int


@availability_router.post("/upload_xlsx")
async def upload_xlsx(
    file: UploadFile = File(...),
    parser: IFileParser = Depends(FileParser),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    file_ext = file.filename.split(".")[-1] if file.filename else ""
    file_content = await file.read()
    data = parser.parse_bytes(file_content, file_ext)

    user_repo = Repository(session, User)
    avail_repo = Repository(session, OfficeAvailability)

    processed_count = 0

    for day_key, names in data.items():
        try:
            day_date = datetime.strptime(day_key, "%Y-%m-%d").date()
        except ValueError:
            continue

        for full_name in names:
            # Split full_name into name and last_name for database query
            # The XLSX parser creates "first_name last_name" format
            name_parts = full_name.split(" ", 1)
            name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            users = await user_repo.query(name=name, last_name=last_name)
            if not users:
                continue

            user = users[0]
            existing = await avail_repo.query(day=day_date, user_id=str(user.id))

            if existing:
                existing[0].present = True
            else:
                new_avail = OfficeAvailability(
                    user_id=str(user.id),
                    day=day_date,
                    present=True,
                )
                await avail_repo.create(new_avail)

            processed_count += 1

    await session.commit()

    return {"message": "Upload processed", "records_processed": processed_count}


@availability_router.get("/{user_id}", response_model=MonthlyAvailabilityResponse)
async def get_user_availability(
    user_id: str,
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    availability_service: AvailabilityService = Depends(get_availability_service),
):
    if str(current_user.id) != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access forbidden")

    today = date.today()
    used_year = year if year else today.year
    used_month = month if month else today.month

    result = await availability_service.get_user_availability(user_id, used_year, used_month, session)

    if isinstance(result, Err):
        raise HTTPException(status_code=404, detail=result.error)

    dto = result.value

    return MonthlyAvailabilityResponse(
        user_id=dto.user_id,
        user_name=dto.user_name,
        year=dto.year,
        month=dto.month,
        availability=[
            DailyAvailabilityResponse(
                date=a.date,
                status=a.status,
                day_of_week=a.day_of_week,
            )
            for a in dto.availability
        ],
        office_days_count=dto.office_days_count,
    )


@availability_router.post("/{user_id}/day", response_model=DailyAvailabilityResponse)
async def update_user_availability_day(
    user_id: str,
    body: UpdateDayRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    availability_service: AvailabilityService = Depends(get_availability_service),
):
    if str(current_user.id) != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access forbidden")

    try:
        target_date = datetime.strptime(body.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    result = await availability_service.update_single_day(user_id, target_date, body.status, session)

    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)

    dto = result.value

    return DailyAvailabilityResponse(
        date=dto.date,
        status=dto.status,
        day_of_week=dto.day_of_week,
    )


@availability_router.post("/{user_id}/batch", response_model=MonthlyAvailabilityResponse)
async def batch_update_availability(
    user_id: str,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    body: BatchUpdateRequest = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    availability_service: AvailabilityService = Depends(get_availability_service),
):
    if str(current_user.id) != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access forbidden")

    try:
        office_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in body.office_dates]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    result = await availability_service.batch_update_month(user_id, year, month, office_dates, session)

    if isinstance(result, Err):
        raise HTTPException(status_code=400, detail=result.error)

    dto = result.value

    return MonthlyAvailabilityResponse(
        user_id=dto.user_id,
        user_name=dto.user_name,
        year=dto.year,
        month=dto.month,
        availability=[
            DailyAvailabilityResponse(
                date=a.date,
                status=a.status,
                day_of_week=a.day_of_week,
            )
            for a in dto.availability
        ],
        office_days_count=dto.office_days_count,
    )


@availability_router.get("/office/{date_str}", response_model=UsersInOfficeResponse)
async def get_users_in_office(
    date_str: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    availability_service: AvailabilityService = Depends(get_availability_service),
):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    users = await availability_service.get_office_users_for_date(target_date, session)

    return UsersInOfficeResponse(
        date=target_date,
        users=users,
        total=len(users),
    )
