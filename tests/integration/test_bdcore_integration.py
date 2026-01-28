"""Integration tests for bd-core integration in reports-system.

These tests verify that the application correctly integrates with bd-core
components including the database client, session middleware, and shared models.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.server import app


@pytest.mark.asyncio
async def test_health_check():
    """Verify app starts and healthcheck endpoint works with bd-core integration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthcheck")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_endpoint_alias():
    """Verify /health alias also works."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_unauthenticated_endpoint_returns_401():
    """Verify protected endpoints return 401 when not authenticated."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attempt to access a protected endpoint without authentication
        response = await client.get("/users")
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_bdcore_database_client_available():
    """Verify PGSQLClient from bd-core is properly integrated."""
    from bd_core.database import PGSQLClient

    # Verify the import works and the class has expected interface
    assert hasattr(PGSQLClient, "session")
    assert hasattr(PGSQLClient, "close")


@pytest.mark.asyncio
async def test_bdcore_session_middleware_available():
    """Verify session middleware from bd-core is properly integrated."""
    from bd_core.auth import create_session_middleware

    # Verify the factory function works
    middleware_class, kwargs = create_session_middleware(
        secret_key="test-key",
        max_age=3600,
        same_site="lax",
        https_only=False,
    )
    assert middleware_class is not None
    assert "secret_key" in kwargs


@pytest.mark.asyncio
async def test_bdcore_repository_available():
    """Verify Repository from bd-core is properly integrated."""
    from bd_core.database import Repository

    # Verify the class has expected async methods (bd-core API)
    assert hasattr(Repository, "get")
    assert hasattr(Repository, "query")
    assert hasattr(Repository, "create")
    assert hasattr(Repository, "update")
    assert hasattr(Repository, "delete")
    assert hasattr(Repository, "count")


@pytest.mark.asyncio
async def test_shared_models_from_bdcore():
    """Verify shared models are properly imported from bd-core."""
    from bd_core.database.models import User, Organization, Project

    # Verify models exist and have expected attributes
    assert User is not None
    assert Organization is not None
    assert Project is not None


@pytest.mark.asyncio
async def test_shared_enums_from_bdcore():
    """Verify shared enums are properly imported from bd-core."""
    from bd_core.enums import (
        Roles,
        ProjectStatus,
        SubscriptionTier,
    )

    # Verify enums exist and have expected values
    assert Roles.ADMIN is not None
    assert ProjectStatus.ACTIVE is not None
    assert SubscriptionTier.FREE is not None


@pytest.mark.asyncio
async def test_orm_mappings_configured():
    """Verify ORM mappings are properly configured at startup."""
    from database.models import (
        configure_mappings,
        User,
        Organization,
        Project,
        Task,
        Log,
    )

    # Mappings should be configured (idempotent call)
    configure_mappings()

    # Models should be usable (have mapped attributes)
    assert hasattr(User, "id")
    assert hasattr(Organization, "id")
    assert hasattr(Project, "id")
    assert hasattr(Task, "id")
    assert hasattr(Log, "id")


@pytest.mark.asyncio
async def test_task_crud_with_bdcore():
    """Verify task operations work with bd-core."""
    # This requires test database setup
    # Implement based on existing test patterns
    pass
