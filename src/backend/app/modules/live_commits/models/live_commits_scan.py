from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey, Boolean
from datetime import datetime

from sqlalchemy.orm import relationship

from app.modules.vc.models.vc import VcTypes
import enum
from app.modules.pr.models.pr_scan import StatusEnum
from app.core.db import Base

# Define the ScanStatus Enum


class ScanStatus(enum.Enum):
    passed = "passed"
    failed = "failed"

class LiveCommitScanType(str, enum.Enum):
    SECRET = 'SECRET'
    VULNERABILITY = 'VULNERABILITY'

class LiveCommitScan(Base): 
    __tablename__ = "live_commits_scan"

    id = Column(Integer, primary_key=True, index=True)
    vc_id = Column(Integer, ForeignKey("vcs.id"), nullable=False)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    webhook_id = Column(Integer, nullable=False)
    live_commit_id = Column(Integer, ForeignKey("live_commits.id"), nullable=False)

    status = Column(
        Enum(StatusEnum),
        default=StatusEnum.pending,
        nullable=False)
    scan_status = Column(
        Enum(ScanStatus),
        default=ScanStatus.passed,
        nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    live_commit = relationship('LiveCommit', back_populates='scans')
    # vc = relationship('VC', back_populates='live_commit_scan')
    # repository = relationship('Repo', back_populates='live_commit_scan')

    scan_type = Column(Enum(LiveCommitScanType), default=LiveCommitScanType.SECRET, nullable=True)
        # New relationships with Secrets and Vulnerabilities
    secrets = relationship("Secrets", back_populates="live_commit_scan", cascade="all, delete-orphan")
    vulnerabilities = relationship("Vulnerability", back_populates="live_commit_scan", cascade="all, delete-orphan")