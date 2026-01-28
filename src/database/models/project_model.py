from sqlalchemy import (
    JSON,
    Text,
    Table,
    Column,
    String,
    Boolean,
    DateTime,
    BigInteger,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.models import Project
from database.models.mapper import mapper_registry

project_table = Table(
    "projects",
    mapper_registry.metadata,
    Column("id", String(26), primary_key=True),
    Column("name", String(255)),
    Column("description", Text()),
    Column(
        "organization_id",
        String(26),
        ForeignKey("organizations.id"),
        nullable=False,
    ),
    Column("user_id", String(26), ForeignKey("users.id"), nullable=False),
    Column("parent_project_id", String(26), ForeignKey("projects.id")),
    Column("status", BigInteger(), default=0),
    Column("is_template", Boolean(), default=False),
    Column("is_public", Boolean(), default=False),
    Column("file_count", BigInteger(), default=0),
    Column("storage_used", BigInteger(), default=0),
    Column("tags", JSON, default=lambda: []),
    Column("pending_invites", JSON, default=lambda: {}),
    Column("starred_by", JSON, default=lambda: []),
    Column("last_activity", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), onupdate=func.now()),
    Column("archived_at", DateTime(timezone=True)),
)

project_members = Table(
    "project_members",
    mapper_registry.metadata,
    Column(
        "project_id", String(26), ForeignKey("projects.id"), primary_key=True
    ),
    Column("user_id", String(26), ForeignKey("users.id"), primary_key=True),
    Column("permissions", BigInteger()),
)

mapper_registry.map_imperatively(
    Project,
    project_table,
    properties={
        "organization": relationship(
            "Organization", back_populates="projects", lazy="selectin"
        ),
        "user": relationship(
            "User", back_populates="projects", lazy="selectin"
        ),
        "parent_project": relationship(
            "Project",
            remote_side=[project_table.c.id],
            back_populates="child_projects",
            lazy="selectin",
        ),
        "child_projects": relationship(
            "Project",
            remote_side=[project_table.c.parent_project_id],
            back_populates="parent_project",
            lazy="selectin",
        ),
        "members": relationship(
            "User",
            secondary=project_members,
            back_populates="project_memberships",
            lazy="selectin",
        ),
        "tasks": relationship(
            "Task",
            back_populates="project",
            cascade="all, delete-orphan",
            lazy="selectin",
        ),
    },
)
