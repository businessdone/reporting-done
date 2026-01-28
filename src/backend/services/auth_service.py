from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from backend.types.result import Result, Ok, Err
from backend.types.auth import AuthCredentials, AuthenticatedUser
from backend.types.identifiers import UserId
from backend.exceptions import InvalidCredentialsError
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User
from core.enums import Permissions
from businessdone_core.database import Repository


class AuthService:
    __slots__ = ("_hasher",)
    
    def __init__(self) -> None:
        self._hasher = PasswordHasher()
    
    def authenticate(
        self,
        credentials: AuthCredentials,
        session: AsyncSession,
    ) -> Result[AuthenticatedUser, str]:
        with session as s:
            repo = Repository(s, User)
            users = repo.query(email=credentials.email)
            
            if not users:
                return Err("Invalid email or password")
            
            user = users[0]
            
            if not self.verify_password(credentials.password, user.password):
                return Err("Invalid email or password")
            
            is_admin = Permissions(user.permissions) == Permissions.ADMIN
            
            return Ok(AuthenticatedUser(
                user_id=UserId(user.id),
                email=user.email,
                full_name=user.full_name,
                permissions=user.permissions,
                is_admin=is_admin,
            ))
    
    def get_user_by_id(
        self,
        user_id: str,
        session: AsyncSession,
    ) -> Result[AuthenticatedUser, str]:
        with session as s:
            repo = Repository(s, User)
            user = repo.get(user_id)
            
            if not user:
                return Err("User not found")
            
            is_admin = Permissions(user.permissions) == Permissions.ADMIN
            
            return Ok(AuthenticatedUser(
                user_id=UserId(user.id),
                email=user.email,
                full_name=user.full_name,
                permissions=user.permissions,
                is_admin=is_admin,
            ))
    
    def hash_password(self, password: str) -> str:
        return self._hasher.hash(password)
    
    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            self._hasher.verify(hashed, password)
            return True
        except VerifyMismatchError:
            return False
    
    def needs_rehash(self, hashed: str) -> bool:
        return self._hasher.check_needs_rehash(hashed)

