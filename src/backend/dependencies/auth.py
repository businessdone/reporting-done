"""Authentication dependencies for FastAPI."""

from fastapi import Depends, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import User
from core.enums import Permissions
from backend.dependencies.db_session import get_db_session


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Get the currently authenticated user."""
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_current_user_optional(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Get the currently authenticated user, or None if not authenticated."""
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def is_admin(current_user: User) -> bool:
    """Check if the user has admin permissions."""
    return Permissions(current_user.permissions) == Permissions.ADMIN


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that requires the current user to be an admin."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def validate_csrf(request: Request) -> None:
    """Validate CSRF token from request."""
    csrf_token_in_session = request.session.get("csrftoken", "")
    csrf_token = request.headers.get("X-CSRFToken", "")

    if not csrf_token:
        form = await request.form()
        csrf_token = form.get("csrftoken", "")

    if not csrf_token or csrf_token != csrf_token_in_session:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
