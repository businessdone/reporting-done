"""Organization model mapping with reports-specific relationships.

Uses bd-core's Organization model and organization_table, adding
reports-specific relationships via configure_organization_mapping().
"""

from sqlalchemy.orm import relationship

from businessdone_core.database.models import Organization
from businessdone_core.database.models.organization import organization_table
from businessdone_core.database.models.user import user_table
from businessdone_core.database.registry import mapper_registry


def configure_organization_mapping() -> None:
    """Configure Organization model with reports-specific relationships.

    This function maps the Organization class to organization_table with
    all relationships needed by reports-system:
    - users: Users belonging to this organization (shared)
    - projects: Projects in this organization (shared)
    """
    mapper_registry.map_imperatively(
        Organization,
        organization_table,
        properties={
            "users": relationship(
                "User",
                back_populates="organization",
                cascade="all, delete-orphan",
                lazy="selectin",
                foreign_keys=[user_table.c.organization_id],
            ),
            "projects": relationship(
                "Project",
                back_populates="organization",
                cascade="all, delete-orphan",
                lazy="selectin",
            ),
        },
    )


__all__ = ["Organization", "organization_table", "configure_organization_mapping"]
