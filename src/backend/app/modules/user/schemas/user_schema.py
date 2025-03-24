from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import enum
from app.modules.user.models.user import UserRole

class UserBase(BaseModel):
    username: str
    role: UserRole
    user_email: str
    active: bool = True


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    group_id: Optional[int] = None
    added_by_uid: Optional[int]
    updated_by_uid: Optional[int]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    role: UserRole
    active: bool
    user_email: str
