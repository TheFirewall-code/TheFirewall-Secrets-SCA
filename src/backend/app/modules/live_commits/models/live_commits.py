from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.db import Base


class LiveCommit(Base):
    __tablename__ = "live_commits"

    id = Column(Integer, primary_key=True, index=True)
    vc_id = Column(Integer, ForeignKey("vcs.id"), nullable=False)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    branch = Column(String, nullable=False)
    created_at = Column(
        DateTime(
            timezone=True),
        server_default=func.now(),
        nullable=False)
    commit_id = Column(String, nullable=False)
    commit_url = Column(String, nullable=False)
    author_name = Column(String, nullable=False)
    commit_msg = Column(String, nullable=False)
    other_details = Column(JSON, nullable=True)

    # Relationships
    vc = relationship("VC", back_populates="live_commits")
    repository = relationship("Repo", back_populates="live_commits")
    scans = relationship('LiveCommitScan', back_populates='live_commit')
