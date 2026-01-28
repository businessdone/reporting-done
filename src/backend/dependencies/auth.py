from fastapi import Depends, Request, HTTPException
from fastapi.responses import RedirectResponse

from core.models import User
from core.enums import Permissions
from backend.protocols.session import ISession
from backend.dependencies.db_session import get_session
from database.repositories.repository import Repository


def get_current_user(
    request: Request,
    session: ISession = Depends(get_session),
) -> User:
    user_id = request.session.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    with session as s:
        repository = Repository(s, User)
        user = repository.get(user_id)
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user


def get_current_user_optional(
    request: Request,
    session: ISession = Depends(get_session),
) -> User | None:
    user_id = request.session.get("user_id")
    
    if not user_id:
        return None
    
    with session as s:
        repository = Repository(s, User)
        return repository.get(user_id)


def is_admin(current_user: User) -> bool:
    return Permissions(current_user.permissions) == Permissions.ADMIN


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def validate_csrf(request: Request) -> None:
    csrf_token_in_session = request.session.get("csrftoken", "")
    csrf_token = request.headers.get("X-CSRFToken", "")
    
    if not csrf_token:
        form = await request.form()
        csrf_token = form.get("csrftoken", "")
    
    if not csrf_token or csrf_token != csrf_token_in_session:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
