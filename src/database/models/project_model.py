"""Project model mapping with reports-specific relationships.

Uses bd-core's Project model and project_table, adding reports-specific
relationships (tasks) via configure_project_mapping().
"""

from sqlalchemy.orm import class_mapper, relationship
from sqlalchemy.orm.exc import UnmappedClassError

from bd_core.database.models import Project
from bd_core.database.models.project import project_members_table, project_table
from bd_core.database.registry import mapper_registry

# Re-export with the name used in this codebase for backwards compatibility
project_members = project_members_table


def configure_project_mapping() -> None:
    """Configure Project model with reports-specific relationships.

    This function maps the Project class to project_table with all relationships
    needed by reports-system:
    - organization: The organization this project belongs to (shared)
    - user: The user who created this project (shared)
    - parent_project: Parent project if this is a sub-project (shared)
    - child_projects: Child sub-projects (shared)
    - members: Users who are members of this project (shared)
    - tasks: Tasks in this project (reports-specific)

    This function is idempotent - calling it multiple times is safe.
    """
    try:
        class_mapper(Project)
        return  # Already mapped, skip
    except UnmappedClassError:
        pass  # Not mapped, proceed

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


__all__ = [
    "Project",
    "project_table",
    "project_members",
    "project_members_table",
    "configure_project_mapping",
]
