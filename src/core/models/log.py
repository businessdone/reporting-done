from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ulid import ULID

from core.enums.task_status import TaskStatus


class Log:
    if TYPE_CHECKING:
        id: str
        created_at: datetime
        task_id: str
        task_name: str
        description: str
        user_id: str
        user_name: str
        project_id: str
        project_name: str
        hours_spent: float
        task_status: str

    def __init__(
        self,
        id: str,
        created_at: datetime,
        task_id: str,
        task_name: str,
        description: str,
        user_id: str,
        user_name: str,
        project_id: str,
        project_name: str,
        hours_spent: float,
        task_status: str,
    ):
        self.id = id
        self.created_at = created_at
        self.task_id = task_id
        self.task_name = task_name
        self.description = description
        self.user_id = user_id
        self.user_name = user_name
        self.project_id = project_id
        self.project_name = project_name
        self.hours_spent = hours_spent
        self.task_status = task_status

    @property
    def _id(self) -> ULID:
        return ULID.from_str(self.id)

    @property
    def _task_id(self) -> ULID:
        return ULID.from_str(self.task_id)

    @property
    def _user_id(self) -> ULID:
        return ULID.from_str(self.user_id)

    @property
    def _project_id(self) -> ULID:
        return ULID.from_str(self.project_id)

    @property
    def _task_status(self) -> TaskStatus:
        return TaskStatus(self.task_status)

    def to_dict(self, visited: set[int] | None = None) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "task_id": self.task_id,
            "task_name": self.task_name,
            "description": self.description,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "hours_spent": self.hours_spent,
            "task_status": self.task_status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Log":
        # Support legacy field name
        created_at_raw = data.get("created_at") or data.get("timestamp")
        created_at: datetime
        if isinstance(created_at_raw, str):
            created_at = datetime.fromisoformat(created_at_raw)
        elif isinstance(created_at_raw, int):
            # Legacy support: convert epoch timestamp
            created_at = datetime.fromtimestamp(created_at_raw, tz=timezone.utc)
        elif isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        else:
            created_at = datetime.now(timezone.utc)

        # Support legacy field name
        hours_spent = data.get("hours_spent", data.get("hours_spent_today", 0.0))

        return cls(
            id=data["id"],
            created_at=created_at,
            task_id=data["task_id"],
            task_name=data["task_name"],
            description=data["description"],
            user_id=data["user_id"],
            user_name=data["user_name"],
            project_id=data["project_id"],
            project_name=data["project_name"],
            hours_spent=hours_spent,
            task_status=data["task_status"],
        )
