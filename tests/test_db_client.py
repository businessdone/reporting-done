"""Tests for PGSQLClient from bd-core."""

import inspect


def test_db_client_initialization():
    """Verify PGSQLClient can be initialized."""
    from businessdone_core.database import PGSQLClient

    # Test with dummy config (won't actually connect)
    client = PGSQLClient(
        db_user="test",
        db_password="test",
        db_host="localhost",
        db_port=5432,
        db_name="test",
    )

    assert client is not None
    assert hasattr(client, "session")
    assert hasattr(client, "engine")


def test_db_client_has_close_method():
    """Verify PGSQLClient has async close method."""
    from businessdone_core.database import PGSQLClient

    client = PGSQLClient(
        db_user="test",
        db_password="test",
        db_host="localhost",
        db_port=5432,
        db_name="test",
    )

    assert hasattr(client, "close")
    # close() is an async method
    assert inspect.iscoroutinefunction(client.close)


def test_session_middleware_creation():
    """Verify create_session_middleware from bd-core works."""
    from businessdone_core.auth import create_session_middleware
    from starlette.middleware.sessions import SessionMiddleware

    middleware_class, kwargs = create_session_middleware(
        secret_key="test-secret-key",
        max_age=60 * 60 * 24,
        same_site="lax",
        https_only=False,
    )

    assert middleware_class is SessionMiddleware
    assert kwargs["secret_key"] == "test-secret-key"
    assert kwargs["max_age"] == 60 * 60 * 24
    assert kwargs["same_site"] == "lax"
    assert kwargs["https_only"] is False
