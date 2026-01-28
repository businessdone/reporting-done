"""Database session dependencies.

Provides sync sessions for backward compatibility with existing codebase.
The PGSQLClient in app.state manages the connection pool for async operations,
while this module provides sync sessions using the same connection parameters.
"""

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.protocols.session import ISession
from config.env import ENV
from database.sessions.sqlalchemy_session import SQLAlchemySession


def _create_sync_engine():
    """Create a sync SQLAlchemy engine using the same connection parameters."""
    url = URL.create(
        drivername="postgresql+psycopg",
        username=ENV.DB_USER,
        password=ENV.DB_PASSWORD,
        host=ENV.DB_HOST,
        port=ENV.DB_PORT,
        database=ENV.DB_NAME,
    )
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=False,
    )


# Create module-level sync engine and session factory
_sync_engine = _create_sync_engine()
_SyncSessionFactory = sessionmaker(bind=_sync_engine, autocommit=False, autoflush=False)


def _get_sync_session() -> Session:
    """Create a new sync SQLAlchemy session."""
    return _SyncSessionFactory()


async def get_session() -> ISession:
    """Get a session wrapped in ISession interface.

    Note: This returns a sync session for backward compatibility.
    Future migration may convert this to async sessions.
    """
    return SQLAlchemySession(_get_sync_session())


def get_session_sync() -> ISession:
    """Get a sync session wrapped in ISession interface."""
    return SQLAlchemySession(_get_sync_session())


def get_session_factory():
    """Get the session factory function."""
    return get_session_sync
