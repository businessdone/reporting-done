"""Tests for mapper migration to bd-core."""


def test_mapper_registry_from_bdcore() -> None:
    """Verify mapper_registry comes from bd-core."""
    from database.models.mapper import mapper_registry
    from businessdone_core.database.registry import mapper_registry as bdcore_registry

    assert mapper_registry is bdcore_registry


def test_shared_tables_from_bdcore() -> None:
    """Verify shared tables (user, organization, project) come from bd-core."""
    from database.models import user_table, organization_table, project_table
    from businessdone_core.database.models import (
        user_table as bdcore_user_table,
        organization_table as bdcore_organization_table,
        project_table as bdcore_project_table,
    )

    assert user_table is bdcore_user_table
    assert organization_table is bdcore_organization_table
    assert project_table is bdcore_project_table


def test_project_members_table_from_bdcore() -> None:
    """Verify project_members table comes from bd-core."""
    from database.models import project_members
    from businessdone_core.database.models import (
        project_members_table as bdcore_project_members,
    )

    assert project_members is bdcore_project_members


def test_shared_models_from_bdcore() -> None:
    """Verify User, Organization, Project models come from bd-core."""
    from database.models import User, Organization, Project
    from businessdone_core.database.models import (
        User as BdcoreUser,
        Organization as BdcoreOrganization,
        Project as BdcoreProject,
    )

    assert User is BdcoreUser
    assert Organization is BdcoreOrganization
    assert Project is BdcoreProject


def test_table_sets_documented() -> None:
    """Verify SHARED_TABLES and REPORTS_TABLES are properly documented."""
    from database.models.mapper import SHARED_TABLES, REPORTS_TABLES

    # Shared tables (managed by ocrdone-backend)
    expected_shared = {
        "users",
        "organizations",
        "projects",
        "project_members",
        "oauth_states",
        "files",
    }
    assert SHARED_TABLES == expected_shared

    # Reports-specific tables
    expected_reports = {"tasks", "task_logs", "events", "office_availability"}
    assert REPORTS_TABLES == expected_reports
