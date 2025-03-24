from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, String
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db import Base
from app.modules.incidents.models.incident_model import IncidentStatusEnum
import enum


class Action(enum.Enum):
    INCIDENT_OPENED = "incident opened"
    INCIDENT_IN_PROGRESS = "incident in-progress"
    INCIDENT_CLOSED = "incident closed"
    COMMENT_ADDED = "comment added"
    SEVERITY_UPDATED = "severity updated"


class Activity(Base):
    __tablename__ = "activity"

    id = Column(Integer, primary_key=True, index=True)

    # Use Action enum for the action column
    action = Column(Enum(Action), nullable=False)

    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ForeignKey to Incidents
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    incident = relationship("Incidents", back_populates="activities")

    # Optional: Track the user who performed the action
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")

    # One-to-one relationship with Comment
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    comment = relationship("Comments", back_populates="activity")
