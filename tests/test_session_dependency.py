# tests/test_session_dependency.py
"""Tests for the async database session dependency."""

import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_get_db_session_yields_async_session():
    """Verify db session dependency yields AsyncSession."""
    from backend.dependencies.db_session import get_db_session
    from sqlalchemy.ext.asyncio import AsyncSession

    # Mock request with db client
    mock_request = MagicMock()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_db = MagicMock()
    mock_db.session = AsyncMock(return_value=mock_session)
    mock_request.app.state.db = mock_db

    # The dependency is an async generator
    gen = get_db_session(mock_request)
    session = await gen.__anext__()

    assert session is mock_session


@pytest.mark.asyncio
async def test_get_db_session_calls_db_client_session():
    """Verify the dependency calls db client's session method."""
    from backend.dependencies.db_session import get_db_session

    mock_request = MagicMock()
    mock_session = AsyncMock()
    mock_db = MagicMock()
    mock_db.session = AsyncMock(return_value=mock_session)
    mock_request.app.state.db = mock_db

    gen = get_db_session(mock_request)
    await gen.__anext__()

    # Verify session() was called on db client
    mock_db.session.assert_called_once()
