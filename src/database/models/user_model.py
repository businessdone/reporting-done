"""User model mapping with reports-specific relationships.

Uses bd-core's User model and user_table, adding reports-specific
relationships (tasks, task_logs) via configure_user_mapping().
"""

from sqlalchemy.orm import class_mapper, relationship
from sqlalchemy.orm.exc import UnmappedClassError

from bd_core.database.models import User
from bd_core.database.models.user import user_table
from bd_core.database.registry import mapper_registry


def configure_user_mapping() -> None:
    """Configure User model with reports-specific relationships.

    This function maps the User class to user_table with all relationships
    needed by reports-system:
    - organization: The user's organization (shared)
    - projects: Projects created by the user (shared)
    - project_memberships: Projects the user is a member of (shared)
    - tasks: Tasks assigned to the user (reports-specific)
    - task_logs: Log entries created by the user (reports-specific)

    This function is idempotent - calling it multiple times is safe.
    """
    try:
        class_mapper(User)
        return  # Already mapped, skip
    except UnmappedClassError:
        pass  # Not mapped, proceed

    mapper_registry.map_imperatively(
        User,
        user_table,
        properties={
            "projects": relationship(
                "Project", back_populates="user", lazy="selectin"
            ),
            "project_memberships": relationship(
                "Project",
                secondary="project_members",
                back_populates="members",
                lazy="selectin",
            ),
            "organization": relationship(
                "Organization",
                back_populates="users",
                lazy="selectin",
                foreign_keys=[user_table.c.organization_id],
            ),
            "tasks": relationship(
                "Task",
                back_populates="user",
                cascade="all, delete-orphan",
                lazy="selectin",
            ),
            "task_logs": relationship(
                "Log",
                back_populates="user",
                cascade="all, delete-orphan",
                lazy="selectin",
            ),
        },
    )


__all__ = ["User", "user_table", "configure_user_mapping"]
