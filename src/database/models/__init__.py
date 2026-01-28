"""Database models for reports-system.

This module provides:
1. Shared models and tables from bd-core (User, Organization, Project)
2. Reports-specific models and tables (Task, Log, Event, OfficeAvailability)
3. Configuration functions for setting up ORM mappings

Usage:
    from database.models import configure_mappings
    configure_mappings()  # Call once at application startup
"""

from .mapper import REPORTS_TABLES, SHARED_TABLES, mapper_registry

# Shared models and tables from bd-core
from .user_model import User, configure_user_mapping, user_table
from .organization_model import (
    Organization,
    configure_organization_mapping,
    organization_table,
)
from .project_model import (
    Project,
    configure_project_mapping,
    project_members,
    project_members_table,
    project_table,
)

# Reports-specific models and tables
# Note: log_mapper must be imported before task_mapper due to column_property dependency
from .log_mapper import Log, task_log_table  # noqa: E402
from .task_mapper import Task, task_table  # noqa: E402
from .event_mapper import Event, event_table  # noqa: E402
from .availability_mapper import (  # noqa: E402
    OfficeAvailability,
    office_availability_table,
)


def configure_mappings() -> None:
    """Configure all ORM mappings for reports-system.

    This function should be called once at application startup to set up
    all imperative mappings. The bd-core models (User, Organization, Project)
    are mapped with reports-specific relationships.

    Note: Reports-specific models (Task, Log, Event, OfficeAvailability) are
    mapped at import time in their respective mapper modules.
    """
    configure_user_mapping()
    configure_organization_mapping()
    configure_project_mapping()


__all__ = [
    # Registry and table sets
    "mapper_registry",
    "SHARED_TABLES",
    "REPORTS_TABLES",
    # Configuration
    "configure_mappings",
    "configure_user_mapping",
    "configure_organization_mapping",
    "configure_project_mapping",
    # Shared models
    "User",
    "user_table",
    "Organization",
    "organization_table",
    "Project",
    "project_table",
    "project_members",
    "project_members_table",
    # Reports-specific models
    "Task",
    "task_table",
    "Log",
    "task_log_table",
    "Event",
    "event_table",
    "OfficeAvailability",
    "office_availability_table",
]
