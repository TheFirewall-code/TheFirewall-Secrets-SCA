from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.db import Base
import enum


class VcTypes(str, enum.Enum):
    bitbucket = "bitbucket"
    github = "github"
    gitlab = "gitlab"


class VC(Base):
    __tablename__ = 'vcs'

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(VcTypes), nullable=False)
    token = Column(String, nullable=False)
    url = Column(String, nullable=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    added_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_by = Column(Integer, nullable=False)
    updated_by = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)

    # Relationships
    webhook_configs = relationship('WebhookConfig', back_populates='vc')
    repositories = relationship('Repo', back_populates='vc')
    pr_scan = relationship('PRScan', back_populates='vc')

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)

    live_commits = relationship("LiveCommit", back_populates="vc")

