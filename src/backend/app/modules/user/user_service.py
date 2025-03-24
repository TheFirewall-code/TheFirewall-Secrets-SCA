from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy import update
from app.modules.user.models.user import User
from app.modules.user.schemas.user_schema import UserCreate, UserUpdate
from app.core.logger import logger
from app.core.security import get_password_hash, decode_token
from fastapi import HTTPException, status
from app.utils.pagination import paginate
from sqlalchemy.sql import func


async def get_user_by_id(db: AsyncSession, user_id: int) -> User:
    logger.info(f"Fetching user with id: {user_id}")
    result = await db.execute(select(User).where(User.id == user_id).options(joinedload(User.added_by)))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User:
    logger.info(f"Fetching user with username: {username}")
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: UserCreate, current_user: User):
    existing_user = await get_user_by_username(db, user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    logger.info(f"Creating user with username: {user.username}")
    db_user = User(
        username=user.username,
        user_email=user.user_email,
        hashed_password=get_password_hash(
            user.password),
        role=user.role,
        added_by_uid=current_user.id,
        updated_by_uid=current_user.id)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_all_users(
    db: AsyncSession,
    username: Optional[str] = None,
    page: int = 1,
    limit: int = 10
):

    # Base query
    query = select(User)
    if username:
        query = query.where(User.username.ilike(f"%{username}%"))

    # Calculate total count
    total_count_query = select(func.count()).select_from(query.subquery())
    total_count_result = await db.execute(total_count_query)
    total_count = total_count_result.scalar()

    # Apply pagination
    pagination = paginate(query, total_count, page, limit)
    paginated_query = pagination["query"]

    # Fetch paginated results
    result = await db.execute(paginated_query)
    users = result.scalars().all()

    # Return paginated response
    return {
        "data": users, **pagination["meta"]
    }



async def update_user(
        db: AsyncSession,
        user_id: int,
        user_update: UserUpdate,
        current_user: User):
    logger.info(f"Updating user with id: {user_id}")
    stmt = (
        update(User) .where(
            User.id == user_id) .values(
            role=user_update.role,
            active=user_update.active,
            updated_by_uid=current_user.id,
            user_email=user_update.user_email) .execution_options(
                synchronize_session="fetch"))
    await db.execute(stmt)
    await db.commit()
    return await get_user_by_id(db, user_id)


async def delete_user(db: AsyncSession, user_id: int):
    logger.info(f"Attempting to delete user with id: {user_id}")
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.username == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete an admin user",
        )

    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(active=False)
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()
    logger.info(f"User with id: {user_id} has been deactivated.")
    return await get_user_by_id(db, user_id)



async def update_user_password(
        db: AsyncSession,
        user_id: int,
        new_password: str,
        current_user: User):
    stmt = (
        update(User) .where(
            User.id == user_id) .values(
            hashed_password=get_password_hash(new_password),
            updated_by_uid=current_user.id))
    await db.execute(stmt)
    await db.commit()
    logger.info(f"Password updated for user id: {user_id}")
    return await get_user_by_id(db, user_id)


async def get_current_user_data(db: AsyncSession, token: str) -> User:
    payload = decode_token(token)
    user_id = payload['user_id']
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found")
    return user
