# tests/test_model_migration.py
"""Tests to verify domain models are correctly migrated from bd-core."""


def test_models_from_bdcore():
    """Verify shared models come from bd-core."""
    from core.models import User, Organization, Project
    import bd_core.database.models as bdcore_models

    # Verify they're the same classes
    assert User is bdcore_models.User
    assert Organization is bdcore_models.Organization
    assert Project is bdcore_models.Project


def test_reports_specific_models_preserved():
    """Reports-specific models still work."""
    from core.models import Task, Log, Event, OfficeAvailability

    assert Task is not None
    assert Log is not None
    assert Event is not None
    assert OfficeAvailability is not None
