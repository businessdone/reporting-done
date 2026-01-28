# tests/test_enum_migration.py
"""Tests to verify enums are correctly re-exported from bd-core."""


def test_enums_from_bdcore():
    """Verify enums are re-exported from bd-core."""
    from core.enums import (
        Roles,
        Permissions,
        UserStatus,
        OrganizationStatus,
        ProjectStatus,
    )

    # Verify values match expected
    assert Roles.VIEWER.value == 1
    assert Roles.EDITOR.value == 2
    assert Roles.ADMIN.value == 3
    assert Roles.OWNER.value == 4

    # Verify permissions have expected flags
    assert hasattr(Permissions, "VIEW")
    assert hasattr(Permissions, "EDIT")
    assert hasattr(Permissions, "ALL")

    # Verify status enums
    assert UserStatus.ACTIVE.value == 1
    assert OrganizationStatus.ACTIVE.value == 1
    assert ProjectStatus.ACTIVE.value == 2


def test_subscription_tier_preserved():
    """bd-core's SubscriptionTier should work."""
    from core.enums import SubscriptionTier

    assert SubscriptionTier.FREE is not None
    assert SubscriptionTier.FREE.value == "Free"
    assert SubscriptionTier.TIER_1.value == "Tier 1"


def test_task_status_is_local():
    """TaskStatus should remain a local reports-specific enum."""
    from core.enums import TaskStatus

    assert TaskStatus.PLANNING.value == "Planning"
    assert TaskStatus.DONE.value == "Done"


def test_flag_base_available():
    """FlagBase should be available from bd-core."""
    from core.enums import FlagBase

    assert FlagBase is not None


def test_project_permissions_available():
    """ProjectPermissions should be available from bd-core."""
    from core.enums import ProjectPermissions

    assert hasattr(ProjectPermissions, "VIEW")
    assert hasattr(ProjectPermissions, "EDIT")
    assert hasattr(ProjectPermissions, "CONTRIBUTOR")


def test_file_status_available():
    """FileStatus should be available from bd-core."""
    from core.enums import FileStatus

    assert FileStatus.QUEUED.value == "queued"
    assert FileStatus.PROCESSING.value == "processing"
    assert FileStatus.READY.value == "ready"
