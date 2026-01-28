"""Database session dependency for FastAPI."""

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from businessdone_core.database import PGSQLClient


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session.

    Usage in routes:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    db_client: PGSQLClient = request.app.state.db
    session = await db_client.session()
    try:
        yield session
    finally:
        await session.close()


# Alias for backward compatibility during migration
get_session = get_db_session
