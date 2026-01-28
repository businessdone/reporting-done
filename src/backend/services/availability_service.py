from typing import Sequence
from datetime import date, timedelta
import calendar

from backend.types.result import Result, Ok, Err
from backend.types.dtos import AvailabilityDTO, MonthlyAvailabilityDTO, UserDTO, DayAvailabilityStatus
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User, OfficeAvailability
from database.repositories.repository import Repository


class AvailabilityService:
    __slots__ = ()
    
    def get_user_availability(
        self,
        user_id: str,
        year: int,
        month: int,
        session: AsyncSession,
    ) -> Result[MonthlyAvailabilityDTO, str]:
        if not (1 <= month <= 12):
            return Err("Month must be between 1 and 12")
        
        if not (2000 <= year <= 2100):
            return Err("Year must be between 2000 and 2100")
        
        with session as s:
            user_repo = Repository(s, User)
            user = user_repo.get(user_id)
            
            if not user:
                return Err(f"User with id '{user_id}' not found")
            
            avail_repo = Repository(s, OfficeAvailability)
            
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])
            
            records = avail_repo.query(
                user_id=user_id,
                day__gte=first_day,
                day__lte=last_day,
            )
            
            presence_map: dict[date, bool] = {r.day: r.present for r in records}
            
            availability_list: list[AvailabilityDTO] = []
            office_count = 0
            current = first_day
            
            while current <= last_day:
                is_present = presence_map.get(current, False)
                day_of_week = current.weekday()
                
                if day_of_week >= 5:
                    status: DayAvailabilityStatus = "Off"
                elif is_present:
                    status = "Office"
                    office_count += 1
                else:
                    status = "Remote"
                
                availability_list.append(AvailabilityDTO(
                    date=current,
                    status=status,
                    day_of_week=day_of_week,
                ))
                
                current += timedelta(days=1)
            
            return Ok(MonthlyAvailabilityDTO(
                user_id=user.id,
                user_name=user.full_name,
                year=year,
                month=month,
                availability=availability_list,
                office_days_count=office_count,
            ))
    
    def update_single_day(
        self,
        user_id: str,
        day: date,
        status: str,
        session: AsyncSession,
    ) -> Result[AvailabilityDTO, str]:
        status_lower = status.lower()
        valid_statuses = {"office", "remote", "off"}
        
        if status_lower not in valid_statuses:
            return Err(f"Invalid status: '{status}'. Must be Office, Remote, or Off")
        
        day_of_week = day.weekday()
        
        if day_of_week >= 5 and status_lower not in {"off", ""}:
            return Err("Cannot set active work status for weekend days")
        
        with session as s:
            user_repo = Repository(s, User)
            user = user_repo.get(user_id)
            
            if not user:
                return Err(f"User with id '{user_id}' not found")
            
            avail_repo = Repository(s, OfficeAvailability)
            records = avail_repo.query(user_id=user_id, day=day)
            
            is_present = status_lower == "office"
            
            if records:
                records[0].present = is_present
            else:
                new_record = OfficeAvailability(
                    user_id=user_id,
                    day=day,
                    present=is_present,
                )
                avail_repo.create(new_record)
            
            s.commit()
            
            final_status: DayAvailabilityStatus
            if day_of_week >= 5:
                final_status = "Off"
            elif is_present:
                final_status = "Office"
            else:
                final_status = "Remote"
            
            return Ok(AvailabilityDTO(
                date=day,
                status=final_status,
                day_of_week=day_of_week,
            ))
    
    def batch_update_month(
        self,
        user_id: str,
        year: int,
        month: int,
        office_dates: Sequence[date],
        session: AsyncSession,
    ) -> Result[MonthlyAvailabilityDTO, str]:
        if not (1 <= month <= 12):
            return Err("Month must be between 1 and 12")
        
        if not (2000 <= year <= 2100):
            return Err("Year must be between 2000 and 2100")
        
        office_dates_set = set(office_dates)
        
        for d in office_dates_set:
            if d.year != year or d.month != month:
                return Err(f"Date {d} is not in {year}-{month:02d}")
        
        with session as s:
            user_repo = Repository(s, User)
            user = user_repo.get(user_id)
            
            if not user:
                return Err(f"User with id '{user_id}' not found")
            
            avail_repo = Repository(s, OfficeAvailability)
            
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])
            
            existing = avail_repo.query(
                user_id=user_id,
                day__gte=first_day,
                day__lte=last_day,
            )
            
            existing_map: dict[date, OfficeAvailability] = {r.day: r for r in existing}
            
            current = first_day
            while current <= last_day:
                if current.weekday() >= 5:
                    if current in existing_map:
                        existing_map[current].present = False
                    current += timedelta(days=1)
                    continue
                
                is_office = current in office_dates_set
                
                if current in existing_map:
                    existing_map[current].present = is_office
                else:
                    new_record = OfficeAvailability(
                        user_id=user_id,
                        day=current,
                        present=is_office,
                    )
                    avail_repo.create(new_record)
                
                current += timedelta(days=1)
            
            s.commit()
        
        return self.get_user_availability(user_id, year, month, session)
    
    def get_office_users_for_date(
        self,
        target_date: date,
        session: AsyncSession,
    ) -> Sequence[UserDTO]:
        with session as s:
            avail_repo = Repository(s, OfficeAvailability)
            user_repo = Repository(s, User)
            
            records = avail_repo.query(day=target_date, present=True)
            user_ids = [r.user_id for r in records]
            
            if not user_ids:
                return []
            
            users = user_repo.query(in_={User.id: user_ids})
            
            return [UserDTO.model_validate(u.to_dict()) for u in users]

