from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.modules.user.user_service import (
    get_user_by_id,
    create_user,
    get_all_users,
    update_user,
    delete_user,
    get_current_user_data)
from app.modules.user.schemas.user_schema import UserCreate, UserResponse, UserUpdate
from app.core.logger import logger
from app.modules.auth.auth_utils import role_required, get_current_user
from app.modules.user.models.user import UserRole

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse,
             dependencies=[Depends(role_required([UserRole.admin]))])
async def create_new_user(
        user: UserCreate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    logger.info("Request received to create a new user")
    db_user = await create_user(db, user, current_user)
    return db_user


@router.get("/self", response_model=UserResponse)
async def get_self_user(token: str, db: AsyncSession = Depends(get_db)):
    logger.info("Request received to fetch self user data")
    user_data = await get_current_user_data(db, token)
    return user_data


@router.get("/{user_id}", response_model=UserResponse,
            dependencies=[Depends(role_required([UserRole.admin]))])
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    logger.info(f"Request received to fetch user with id: {user_id}")
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found")
    return db_user


@router.get("/", dependencies=[
            Depends(role_required([UserRole.admin, UserRole.user]))])
async def get_users(
    username: Optional[str] = Query(None, description="Filter by username"),
    db: AsyncSession = Depends(get_db)
):
    logger.info(
        f"Request received to fetch users with username filter: {username}")
    users = await get_all_users(db, username)
    return users


@router.put("/{user_id}", response_model=UserResponse,
            dependencies=[Depends(role_required([UserRole.admin]))])
async def update_existing_user(
        user_id: int,
        user_update: UserUpdate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    logger.info(f"Request received to update user with id: {user_id}")
    updated_user = await update_user(db, user_id, user_update, current_user)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found")
    return updated_user


@router.delete("/{user_id}", response_model=UserResponse,
               dependencies=[Depends(role_required([UserRole.admin]))])
async def soft_delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    deleted_user = await delete_user(db, user_id)
    if not deleted_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found")
    return deleted_user
