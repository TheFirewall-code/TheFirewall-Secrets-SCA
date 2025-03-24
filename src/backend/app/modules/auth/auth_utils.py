from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.modules.user.models.user import UserRole
from app.modules.user.user_service import get_user_by_username
from app.core.security import decode_token
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.modules.user.models.user import User
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"
    readonly = "readonly"


async def get_bearer_token(
    credentials: HTTPAuthorizationCredentials = Depends(
        HTTPBearer())):
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header",
        )
    return token


async def get_current_user(
        token: str = Depends(get_bearer_token),
        db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_token(token)
    username: str = payload.get("username")

    from app.modules.licenses.licesses_service import validate_license
    valid = await validate_license(db)
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid license")

    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header",
        )
    return user


def role_required(required_roles: list[UserRole]):
    async def role_checker(
        current_user=Depends(get_current_user)
    ):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this resource",
            )
        return True
    return role_checker
