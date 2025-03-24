from fastapi import APIRouter, Depends, HTTPException, status, Security
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.modules.auth.schemas.auth_schema import Token, LoginRequest, PasswordResetRequest
from app.modules.auth.auth_utils import get_bearer_token
from app.modules.auth.auth_service import (
    authenticate_user,
    create_tokens_for_user,
    reset_password_user_id,
    check_if_first_login,
    reset_password,
    reset_admin_password
)
from app.modules.auth.auth_utils import role_required, get_current_user
from app.modules.user.models.user import UserRole


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/first-login", response_model=bool)
async def check_first_login(db: AsyncSession = Depends(get_db)):
    is_first_login = await check_if_first_login(db)
    return is_first_login


@router.post("/first-login/reset_password", response_model=bool)
async def reset_password(
        new_password: str,
        db: AsyncSession = Depends(get_db)):
    return await reset_admin_password(db, new_password)


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = await create_tokens_for_user(user)
    return {"access_token": access_token}


@router.post("/reset-password",
             response_model=bool,
             dependencies=[Depends(role_required([UserRole.admin,
                                                  UserRole.user,
                                                  UserRole.readonly]))])
async def reset_password(
        payload: PasswordResetRequest,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    return await reset_password_user_id(db, current_user.id, payload.new_password, current_user)


@router.post("/reset-password/{user_id}", response_model=bool,
             dependencies=[Depends(role_required([UserRole.admin]))])
async def reset_password_user(
        user_id: int,
        payload: PasswordResetRequest,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    return await reset_password_user_id(db, user_id, payload.new_password, current_user)

# @router.post("/refresh-token", response_model=Token)
# async def refresh_token(db: AsyncSession = Depends(get_db), token: str = Depends(get_bearer_token)):
#     tokens = await verify_and_refresh_token(db, token)
#     if not tokens:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid refresh token",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     return tokens
