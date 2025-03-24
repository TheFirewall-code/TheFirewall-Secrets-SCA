from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db import Base
import enum


class IncidentStatusEnum(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in-progress"
    CLOSED = "closed"


class IncidentTypeEnum(enum.Enum):
    secret = "secret"
    vulnerability = "vulnerability"

class IncidentClosedBy(enum.Enum):
    USER = "user"
    PROGRAM = "program"


class Incidents(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(IncidentTypeEnum), nullable=False)
    status = Column(
        Enum(IncidentStatusEnum),
        default=IncidentStatusEnum.OPEN,
        nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)
    closed_by = Column(Enum(IncidentClosedBy), nullable=True)

    # 1:1 relationship with Secrets
    secret_id = Column(
        Integer,
        ForeignKey("secrets.id"),
        nullable=True,
        unique=True)
    secret = relationship("Secrets", back_populates="incident")

    # 1:1 relationship with Vulnerability
    vulnerability_id = Column(
        Integer,
        ForeignKey("vulnerability.id"),
        nullable=True,
        unique=True)
    vulnerability = relationship("Vulnerability", back_populates="incident")

    # Relationship to comments and activities
    comments = relationship(
        "Comments",
        back_populates="incident",
        cascade="all, delete-orphan")
    activities = relationship(
        "Activity",
        back_populates="incident",
        cascade="all, delete-orphan")
