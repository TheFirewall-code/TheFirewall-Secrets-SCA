from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db import Base


class Comments(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ForeignKey to Incidents
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    incident = relationship("Incidents", back_populates="comments")

    # Optional: Track the user who made the comment
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")

    # One-to-one relationship with Activity
    activity = relationship(
        "Activity",
        back_populates="comment",
        uselist=False)
