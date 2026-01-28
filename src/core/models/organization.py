from typing import TYPE_CHECKING, List, Optional
from datetime import datetime, timezone

from ulid import ULID

from core.enums import OrganizationStatus, SubscriptionTier

if TYPE_CHECKING:
    from core.models.user import User
    from core.models.project import Project


class Organization:
    """Represents a tenant organization with resource management"""

    if TYPE_CHECKING:
        id: str
        name: str
        owner_id: str  # User ID
        users: List["User"]
        projects: List["Project"]
        status: int
        subscription: str
        created_at: datetime
        updated_at: datetime
        storage_limit: int

    def __init__(
        self,
        name: str,
        owner_id: str,
        subscription: str,
        storage_limit: int,
        id: Optional[str] = None,
        status: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        users: Optional[List["User"]] = None,
        projects: Optional[List["Project"]] = None,
    ):
        self.id = str(id) if id else str(ULID())
        self.name = name
        self.owner_id = owner_id
        self.subscription = subscription
        self.storage_limit = storage_limit

        # Relationships
        self.users = users or []
        self.projects = projects or []

        # Status
        self.status = status or OrganizationStatus.ACTIVE.value

        # Timestamps
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or self.created_at

    @property
    def _id(self) -> ULID:
        return ULID.from_str(self.id) if isinstance(self.id, str) else self.id

    @property
    def status_enum(self) -> OrganizationStatus:
        return OrganizationStatus(self.status)

    @property
    def subscription_tier(self) -> SubscriptionTier:
        return SubscriptionTier(self.subscription)

    @property
    def active_users(self) -> List[str]:
        return [str(user.id) for user in self.users]

    def to_dict(self, visited=None):
        if visited is None:
            visited = set()

        if id(self) in visited:
            return {
                "id": self.id,
                "name": self.name,
                "owner_id": self.owner_id,
                "status": self.status,
                "organization_id": self.id,
            }

        visited.add(id(self))

        return {
            "id": self.id,
            "name": self.name,
            "owner_id": self.owner_id,
            "status": self.status,
            "subscription": self.subscription,
            "storage_limit": self.storage_limit,
            "users": [user.to_dict(visited) for user in self.users],
            "projects": [
                project.to_dict(visited) for project in self.projects
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "organization_id": self.id,
        }

    @classmethod
    def from_dict(cls, data):
        from datetime import datetime

        from core.models.user import User
        from core.models.project import Project

        return cls(
            id=data.get("id"),
            name=data["name"],
            owner_id=data["owner_id"],
            subscription=data["subscription"],
            storage_limit=data["storage_limit"],
            users=[User.from_dict(user) for user in data.get("users", [])],
            projects=[
                Project.from_dict(project)
                for project in data.get("projects", [])
            ],
            status=data.get("status"),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            updated_at=datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else None,
        )
