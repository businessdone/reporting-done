"""Repository pattern for database operations."""

from typing import Any, Type, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class Repository:
    """Async repository for database CRUD operations.

    This repository uses SQLAlchemy's AsyncSession directly.
    All methods are async and should be awaited.
    """

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def create(self, obj: T) -> T:
        """Add an object to the session and flush."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get(self, id: Any) -> T | None:
        """Get an object by its primary key."""
        return await self.session.get(self.model, id)

    async def get_by(self, **filters: Any) -> T | None:
        """Get a single object by filter criteria."""
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        order_by: Any | None = None,
        **filters: Any,
    ) -> list[T]:
        """List objects with optional filtering and pagination."""
        stmt = select(self.model)

        if filters:
            stmt = stmt.filter_by(**filters)

        if order_by is not None:
            stmt = stmt.order_by(order_by)

        if offset is not None:
            stmt = stmt.offset(offset)

        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, obj: T) -> T:
        """Merge and flush an object."""
        merged = await self.session.merge(obj)
        await self.session.flush()
        return merged

    async def delete(self, obj: T) -> None:
        """Delete an object from the session."""
        await self.session.delete(obj)
        await self.session.flush()

    async def count(self, **filters: Any) -> int:
        """Count objects with optional filtering."""
        stmt = select(func.count()).select_from(self.model)
        if filters:
            stmt = stmt.filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one()
