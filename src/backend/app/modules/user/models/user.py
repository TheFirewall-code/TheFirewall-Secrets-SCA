from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"
    readonly = "readonly"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.user)
    user_email = Column(String, unique=True, nullable=False) 
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)
    added_by_uid = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_uid = Column(Integer, ForeignKey("users.id"), nullable=True)
    active = Column(Boolean, default=True)
    

    added_by = relationship(
        "User",
        remote_side=[id],
        backref="added_users",
        foreign_keys=[added_by_uid])
    updated_by = relationship(
        "User",
        remote_side=[id],
        backref="updated_users",
        foreign_keys=[updated_by_uid])

    comments = relationship("WhitelistComment", back_populates="user", cascade="all, delete-orphan")