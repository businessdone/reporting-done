"""Tests for mapper migration to bd-core."""


def test_mapper_registry_from_bdcore() -> None:
    """Verify mapper_registry comes from bd-core."""
    from database.models.mapper import mapper_registry
    from bd_core.database.registry import mapper_registry as bdcore_registry

    assert mapper_registry is bdcore_registry


def test_shared_tables_from_bdcore() -> None:
    """Verify shared tables (user, organization, project) come from bd-core."""
    from database.models import user_table, organization_table, project_table
    from bd_core.database.models import (
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
    from bd_core.database.models import (
        project_members_table as bdcore_project_members,
    )

    assert project_members is bdcore_project_members


def test_shared_models_from_bdcore() -> None:
    """Verify User, Organization, Project models come from bd-core."""
    from database.models import User, Organization, Project
    from bd_core.database.models import (
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


def test_configure_mappings_idempotent() -> None:
    """Verify configure_mappings() can be called multiple times safely."""
    from database.models import configure_mappings

    # Should not raise on multiple calls
    configure_mappings()
    configure_mappings()
    configure_mappings()  # Third call to be thorough


def test_mapped_classes_have_relationships() -> None:
    """Verify relationships are properly configured after mapping."""
    from database.models import configure_mappings
    from core.models import User, Organization, Project
    from sqlalchemy.orm import class_mapper

    configure_mappings()

    # Verify User has expected relationships
    user_mapper = class_mapper(User)
    user_rel_names = {r.key for r in user_mapper.relationships}
    assert "organization" in user_rel_names
    assert "projects" in user_rel_names
    assert "tasks" in user_rel_names
    assert "task_logs" in user_rel_names
    assert "project_memberships" in user_rel_names

    # Verify Organization has expected relationships
    org_mapper = class_mapper(Organization)
    org_rel_names = {r.key for r in org_mapper.relationships}
    assert "users" in org_rel_names
    assert "projects" in org_rel_names

    # Verify Project has expected relationships
    project_mapper = class_mapper(Project)
    project_rel_names = {r.key for r in project_mapper.relationships}
    assert "organization" in project_rel_names
    assert "user" in project_rel_names
    assert "tasks" in project_rel_names
    assert "members" in project_rel_names
    assert "parent_project" in project_rel_names
    assert "child_projects" in project_rel_names
