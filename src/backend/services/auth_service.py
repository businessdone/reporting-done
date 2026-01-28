from sqlalchemy.ext.asyncio import AsyncSession

from bd_core.auth import hash_password, verify_password
from bd_core.database import Repository
from core.models import User
from core.enums import Permissions
from backend.types.result import Result, Ok, Err
from backend.types.auth import AuthCredentials, AuthenticatedUser
from backend.types.identifiers import UserId


class AuthService:
    __slots__ = ()

    async def authenticate(
        self,
        credentials: AuthCredentials,
        session: AsyncSession,
    ) -> Result[AuthenticatedUser, str]:
        repo = Repository(session, User)
        users = await repo.query(email=credentials.email)

        if not users:
            return Err("Invalid email or password")

        user = users[0]

        if not verify_password(user.password, credentials.password):
            return Err("Invalid email or password")

        is_admin = Permissions(user.permissions) == Permissions.ADMIN

        return Ok(AuthenticatedUser(
            user_id=UserId(str(user.id)),
            email=user.email,
            full_name=user.full_name,
            permissions=user.permissions,
            is_admin=is_admin,
        ))

    async def get_user_by_id(
        self,
        user_id: str,
        session: AsyncSession,
    ) -> Result[AuthenticatedUser, str]:
        repo = Repository(session, User)
        user = await repo.get(user_id)

        if not user:
            return Err("User not found")

        is_admin = Permissions(user.permissions) == Permissions.ADMIN

        return Ok(AuthenticatedUser(
            user_id=UserId(str(user.id)),
            email=user.email,
            full_name=user.full_name,
            permissions=user.permissions,
            is_admin=is_admin,
        ))

    def hash_password(self, password: str) -> str:
        return hash_password(password)
