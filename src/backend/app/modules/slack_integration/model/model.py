from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, func
from app.core.db import Base


class SlackIntegration(Base):
    __tablename__ = 'slack_integrations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_on = Column(DateTime, default=func.now(), nullable=False)

    # Foreign key to users table
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    def __repr__(self):
        return (
            f"<SlackIntegration(id={self.id}, "
            f"channel='{self.channel}', "
            f"active={self.active})>"
        )

