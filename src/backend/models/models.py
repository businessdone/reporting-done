from typing import Sequence
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class LogCreateModel(BaseModel):
    task_name: str = Field(max_length=500)
    description: str = Field(max_length=10000)
    hours_spent: float = Field(gt=0, le=24)
    task_status: str
    id: str
    user_id: str
    user_name: str = Field(max_length=255)
    created_at: datetime
    task_id: str

    # Legacy field aliases
    @property
    def hours_spent_today(self) -> float:
        return self.hours_spent

    @property
    def timestamp(self) -> int:
        return int(self.created_at.timestamp())

    model_config = {"str_strip_whitespace": True}


class LogResponseModel(BaseModel):
    id: str
    task_name: str
    description: str
    user_id: str
    user_name: str
    project_id: str
    project_name: str
    hours_spent: float
    task_status: str
    created_at: datetime
    task_id: str

    # Legacy field aliases
    @property
    def hours_spent_today(self) -> float:
        return self.hours_spent

    @property
    def timestamp(self) -> int:
        return int(self.created_at.timestamp())

    model_config = {"from_attributes": True}


class TaskCreateModel(BaseModel):
    project_id: str
    project_name: str = Field(max_length=255)
    user_id: str
    user_name: str = Field(max_length=255)
    title: str = Field(min_length=1, max_length=500)
    hours_required: float = Field(ge=0)
    hours_worked: float = Field(default=0.0, ge=0)
    returned: bool = False
    description: str = Field(max_length=10000)
    status: str | None = None
    created_at: datetime

    # Legacy field alias
    @property
    def timestamp(self) -> int:
        return int(self.created_at.timestamp())

    model_config = {"str_strip_whitespace": True}


class TaskResponseModel(BaseModel):
    id: str
    project_id: str
    project_name: str
    user_id: str
    user_name: str
    title: str
    hours_required: float
    hours_worked: float
    returned: bool = False
    description: str
    logs: Sequence[LogCreateModel] = Field(default_factory=list)
    status: str | None = None
    updated_at: datetime | None = None
    created_at: datetime

    # Legacy field aliases
    @property
    def last_updated(self) -> int | None:
        return int(self.updated_at.timestamp()) if self.updated_at else None

    @property
    def timestamp(self) -> int:
        return int(self.created_at.timestamp())

    model_config = {"from_attributes": True}


class ProjectCreateModel(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    send_email: bool = False
    email: EmailStr | None = None
    archived: bool = False
    
    @field_validator("email", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        if v == "":
            return None
        return v
    
    model_config = {"str_strip_whitespace": True}


class ProjectResponseModel(BaseModel):
    id: str
    name: str
    send_email: bool
    archived: bool
    email: EmailStr | None = None
    developers: Sequence["UserResponseModel"] = Field(default_factory=list)
    tasks: Sequence[TaskResponseModel] = Field(default_factory=list)
    
    @field_validator("email", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        if v == "":
            return None
        return v
    
    model_config = {"from_attributes": True}


class UserCreateModel(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    permissions: int = Field(ge=0)
    
    model_config = {"str_strip_whitespace": True}


class UserProfileUpdateModel(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    permissions: int | None = Field(default=None, ge=0)
    
    model_config = {"str_strip_whitespace": True}


class UserResponseModel(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    permissions: int
    tasks: Sequence[TaskResponseModel] = Field(default_factory=list)
    projects: Sequence["ProjectResponseModel"] = Field(default_factory=list)
    
    model_config = {"from_attributes": True}


class UserLoginModel(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
    
    model_config = {"str_strip_whitespace": True}


class AvailabilityResponseModel(BaseModel):
    id: str
    user_id: str
    day: date
    present: bool
    
    model_config = {"from_attributes": True}


class UserCalendarResponseModel(BaseModel):
    user_id: str
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)
    office_days: Sequence[date] | None = None
    total_office_days: int | None = Field(default=None, ge=0)
    availability: dict[str, bool] | None = None
    
    model_config = {"from_attributes": True}


class DailyAvailabilityResponseModel(BaseModel):
    date: date
    users_in_office: Sequence[UserResponseModel]
    total_in_office: int = Field(ge=0)
    
    model_config = {"from_attributes": True}


UserResponseModel.model_rebuild()
ProjectResponseModel.model_rebuild()
TaskResponseModel.model_rebuild()
LogResponseModel.model_rebuild()
