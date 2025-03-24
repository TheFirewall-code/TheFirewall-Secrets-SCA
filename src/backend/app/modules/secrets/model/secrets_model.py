from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, ARRAY, Float, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from app.core.db import Base

# Scan type enum


class ScanType(PyEnum):
    REPO_SCAN = "repo_scan"
    PR_SCAN = "pr_scan"
    LIVE_COMMIT = "live_commit"

# Severity level enum


class SeverityLevel(PyEnum): 
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATION = "informational"
    UNKNOWN = "unknown"


class Secrets(Base):
    __tablename__ = "secrets"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=True)
    secret = Column(String, nullable=False)
    file = Column(String, nullable=True)
    symlink_file = Column(String, nullable=True)
    line = Column(String, nullable=True)
    start_line = Column(Integer, nullable=True)
    end_line = Column(Integer, nullable=True)
    start_column = Column(Integer, nullable=True)
    end_column = Column(Integer, nullable=True)
    match = Column(Text, nullable=True)
    entropy = Column(Float, nullable=True)
    rule = Column(String, nullable=True)
    fingerprint = Column(String, nullable=True)
    message = Column(String, nullable=True)
    commit = Column(String, nullable=True)
    author = Column(String, nullable=True)
    email = Column(String, nullable=True)
    date = Column(DateTime, nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    branches = Column(ARRAY(String), nullable=True)

    vc_id = Column(Integer, ForeignKey("vcs.id"), nullable=False)

    whitelist_id = Column(Integer, ForeignKey("whitelist.id"), nullable=True)
    whitelisted = Column(Boolean, default=False)

    # New column for scan type
    scan_type = Column(Enum(ScanType), nullable=False)
    severity = Column(
        Enum(SeverityLevel),
        nullable=False,
        default=SeverityLevel.UNKNOWN)  # New column for severity

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)

    # Foreign keys based on the scan type
    repository_id = Column(
        Integer,
        ForeignKey("repositories.id"),
        nullable=True)
    pr_id = Column(Integer, ForeignKey("prs.id"), nullable=True)
    pr_scan_id = Column(Integer, ForeignKey("pr_scans.id"), nullable=True)
    live_commit_id = Column(
        Integer,
        ForeignKey("live_commits.id"),
        nullable=True)
    live_commit_scan_id = Column(
        Integer,
        ForeignKey("live_commits_scan.id"),
        nullable=True)
    commit_id = Column(Integer, nullable=True)
    repository_scan_id = Column(
        Integer,
        ForeignKey("repository_scans.id"),
        nullable=True)

    # Relationships
    repository = relationship("Repo", back_populates="secrets")
    incident = relationship("Incidents", back_populates="secret")
    pr_scan = relationship("PRScan", back_populates="secrets")
    pr = relationship('PR', back_populates='secrets')
    live_commit_scan = relationship("LiveCommitScan", back_populates="secrets")


    score_raw = Column(Float, nullable=True)
    score_normalized = Column(Float, nullable=True)
    score_normalized_on = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<Secrets(description={self.description}, "
            f"file={self.file}, line={self.line})>"
        )

