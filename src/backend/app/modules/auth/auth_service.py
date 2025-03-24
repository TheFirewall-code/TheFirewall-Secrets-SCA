from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.user.user_service import get_user_by_username, update_user_password, get_user_by_id
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.logger import logger
from fastapi import HTTPException
from app.modules.user.models.user import User
from app.modules.licenses.licesses_service import validate_license


async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        logger.warning(f"Authentication failed for user: {username}")
        return False

    if not user.active:
        raise HTTPException(
            status_code=400,
            detail="Cant login in active user, contact admin")

    return user


async def create_tokens_for_user(user):
    access_token = create_access_token(
        {"username": user.username, "role": user.role, "user_id": user.id})
    return access_token
    # refresh_token = create_refresh_token({"username": user.username, "role": user.role})
    # return access_token, refresh_token


async def verify_and_refresh_token(db: AsyncSession, refresh_token: str):
    payload = decode_token(refresh_token)
    if not payload:
        return None

    username = payload.get("username")
    if not username:
        return None

    user = await get_user_by_username(db, username)
    if not user:
        return None

    access_token = create_access_token(
        {"username": user.username, "role": user.role})
    new_refresh_token = create_refresh_token(
        {"username": user.username, "role": user.role})
    return {"access_token": access_token, "refresh_token": new_refresh_token}

# First Login APIs


async def check_if_first_login(db: AsyncSession):
    user = await get_user_by_username(db, "admin")
    if not user:
        return False

    if verify_password("admin", user.hashed_password):
        return True
    return False


async def reset_admin_password(db: AsyncSession, new_password: str):
    first_login = await check_if_first_login(db)
    if not first_login:
        raise HTTPException(status_code=400,
                            detail="Admin password already updated")

    user = await get_user_by_username(db, "admin")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user = await update_user_password(db, user.id, new_password, User())
    logger.info(f"Password reset for user: admin")
    if not user:
        return False
    return True


async def reset_password(
        db: AsyncSession,
        token: str,
        new_password: str,
        current_user: User):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    username = payload.get("username")
    if not username:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user = await update_user_password(db, user.id, new_password, current_user)
    logger.info(f"Password reset for user: {username}")
    if not user:
        return False
    return True


async def reset_password_user_id(
        db: AsyncSession,
        user_id: int,
        new_password: str,
        current_user: User):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user = await update_user_password(db, user.id, new_password, current_user)
    logger.info(f"Password reset for user: {user_id}")
    if not user:
        return False
    return True
