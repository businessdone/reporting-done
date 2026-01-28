from typing import TYPE_CHECKING, Set, Dict, List, Optional
from datetime import datetime, timezone

from ulid import ULID

from core.enums import ProjectStatus

if TYPE_CHECKING:
    from core.models.task import Task
    from core.models.user import User


class Project:
    """
    Sophisticated project management system with support for
    hierarchical organization and granular access control.

    Features:
    - Parent-child project relationships
    - Resource usage tracking
    - Member management
    - Task organization
    """

    if TYPE_CHECKING:
        id: str
        name: str
        description: Optional[str]
        organization_id: str
        user_id: str
        parent_project_id: Optional[str]
        status: ProjectStatus
        is_template: bool
        is_public: bool
        members: List["User"]
        pending_invites: Dict[str, datetime]
        file_count: int
        storage_used: int
        child_projects: List[str]
        tags: List[str]
        starred_by: Set[str]
        last_activity: Optional[datetime]
        created_at: datetime
        updated_at: datetime
        archived_at: Optional[datetime]
        tasks: List["Task"]

    def __init__(
        self,
        name: str,
        organization_id: str,
        user_id: str,
        description: Optional[str] = None,
        id: Optional[str] = None,
        parent_project_id: Optional[str] = None,
        tasks: Optional[List["Task"]] = None,
        status: ProjectStatus = ProjectStatus.ACTIVE,
        is_template: bool = False,
        is_public: bool = False,
        _members: Optional[List["User"]] = None,
        pending_invites: Optional[Dict[str, datetime]] = None,
        file_count: int = 0,
        storage_used: int = 0,
        child_projects: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        starred_by: Optional[Set[str]] = None,
        last_activity: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        archived_at: Optional[datetime] = None,
    ):
        # Core identifiers
        self.id = id or str(ULID())
        self.name = name
        self.description = description
        self.organization_id = organization_id
        self.user_id = user_id
        self.parent_project_id = parent_project_id
        self.tasks = tasks or []

        # State and access management
        self.status = status
        self.is_template = is_template
        self.is_public = is_public

        # Member management
        self.members = _members or []
        self.pending_invites = pending_invites or {}

        # Resource tracking
        self.file_count = file_count
        self.storage_used = storage_used
        self.child_projects = child_projects or []

        # Metadata
        self.tags = tags or []
        self.starred_by = starred_by or set()
        self.last_activity = last_activity

        # Timestamps
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or self.created_at
        self.archived_at = archived_at

    @property
    def _id(self) -> ULID:
        return ULID.from_str(self.id) if isinstance(self.id, str) else self.id

    def to_dict(self, visited=None):
        if visited is None:
            visited = set()

        if id(self) in visited:
            return {
                "id": self.id,
                "name": self.name,
                "organization_id": self.organization_id,
                "user_id": self.user_id,
                "status": self.status.value,
                "project_id": self.id,
            }

        visited.add(id(self))

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "parent_project_id": self.parent_project_id,
            "status": self.status.value,
            "is_template": self.is_template,
            "is_public": self.is_public,
            "members": [member.to_dict(visited) for member in self.members],
            "pending_invites": {
                k: v.isoformat() for k, v in self.pending_invites.items()
            },
            "file_count": self.file_count,
            "storage_used": self.storage_used,
            "child_projects": self.child_projects,
            "tags": self.tags,
            "starred_by": list(self.starred_by),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "archived_at": self.archived_at.isoformat()
            if self.archived_at
            else None,
            "last_activity": self.last_activity.isoformat()
            if self.last_activity
            else None,
            "tasks": [task.to_dict(visited) for task in self.tasks],
        }

    @classmethod
    def from_dict(cls, data):
        from datetime import datetime

        from core.models.task import Task
        from core.models.user import User

        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data.get("description"),
            organization_id=data["organization_id"],
            user_id=data["user_id"],
            parent_project_id=data.get("parent_project_id"),
            status=ProjectStatus(
                data.get("status", ProjectStatus.ACTIVE.value)
            ),
            is_template=data.get("is_template", False),
            is_public=data.get("is_public", False),
            _members=[User.from_dict(m) for m in data.get("members", [])],
            pending_invites={
                k: datetime.fromisoformat(v)
                for k, v in data.get("pending_invites", {}).items()
            },
            file_count=data.get("file_count", 0),
            storage_used=data.get("storage_used", 0),
            child_projects=data.get("child_projects", []),
            tags=data.get("tags", []),
            starred_by=set(data.get("starred_by", [])),
            tasks=[Task.from_dict(t) for t in data.get("tasks", [])],
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            updated_at=datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else None,
            archived_at=datetime.fromisoformat(data["archived_at"])
            if data.get("archived_at")
            else None,
            last_activity=datetime.fromisoformat(data["last_activity"])
            if data.get("last_activity")
            else None,
        )
