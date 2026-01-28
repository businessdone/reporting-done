from fastapi import Depends, Request, APIRouter, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from backend.services import AuthService
from backend.dependencies import get_session
from backend.dependencies.auth import validate_csrf, get_current_user_optional
from backend.protocols.session import ISession
from backend.types.auth import AuthenticatedUser
from backend.types.result import Ok, Err
from core.models import User


auth_router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    message: str
    user_id: str
    email: str
    full_name: str
    is_admin: bool


class LogoutResponse(BaseModel):
    message: str


class CurrentUserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    permissions: int
    is_admin: bool


_auth_service = AuthService()


@auth_router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    body: LoginRequest,
    session: ISession = Depends(get_session),
):
    from backend.types.auth import AuthCredentials
    
    credentials = AuthCredentials(email=body.email, password=body.password)
    result = _auth_service.authenticate(credentials, session)
    
    if isinstance(result, Err):
        raise HTTPException(status_code=401, detail=result.error)
    
    user = result.value
    request.session["user_id"] = user.user_id
    
    return LoginResponse(
        message="Login successful",
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
    )


@auth_router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    csrf_protect=Depends(validate_csrf),
):
    request.session.clear()
    return LogoutResponse(message="Logout successful")


@auth_router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    request: Request,
    session: ISession = Depends(get_session),
):
    user_id = request.session.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = _auth_service.get_user_by_id(user_id, session)
    
    if isinstance(result, Err):
        request.session.clear()
        raise HTTPException(status_code=401, detail="Session expired")
    
    user = result.value
    
    return CurrentUserResponse(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        permissions=user.permissions,
        is_admin=user.is_admin,
    )


@auth_router.get("/csrf-token")
async def get_csrf_token(request: Request):
    token = request.session.get("csrftoken", "")
    return {"csrftoken": token}


@auth_router.get("/check")
async def check_auth(request: Request, session: ISession = Depends(get_session)):
    user_id = request.session.get("user_id")
    
    if not user_id:
        return {"authenticated": False}
    
    result = _auth_service.get_user_by_id(user_id, session)
    
    if isinstance(result, Err):
        return {"authenticated": False}
    
    return {"authenticated": True, "is_admin": result.value.is_admin}

