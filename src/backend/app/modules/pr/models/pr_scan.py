from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey, Boolean, JSON, String
from datetime import datetime
from app.modules.vc.models.vc import VcTypes
import enum
from app.core.db import Base
from sqlalchemy.orm import relationship


class StatusEnum(enum.Enum):
    pending = "pending"
    completed = "completed"
    processing = "processing"
    failed = "failed"

class PRScanType(str, enum.Enum):
    SECRET = 'SECRET'
    VULNERABILITY = 'VULNERABILITY'

class PRScan(Base):
    __tablename__ = "pr_scans"

    id = Column(Integer, primary_key=True, index=True)
    pr_id = Column(Integer, ForeignKey('prs.id'), nullable=False)
    vc_id = Column(Integer, ForeignKey('vcs.id'), nullable=False)
    webhook_id = Column(Integer, nullable=False)
    repo_id = Column(Integer, ForeignKey('repositories.id'), nullable=False)

    vc_type = Column(Enum(VcTypes), nullable=False)
    status = Column(
        Enum(StatusEnum),
        default=StatusEnum.pending,
        nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    block_status = Column(Boolean, default=False)

    other_details = Column(JSON, nullable=True)
    stat_url = Column(String, nullable=True)

    pr = relationship('PR', back_populates='scans')
    vc = relationship('VC', back_populates='pr_scan')
    repository = relationship('Repo', back_populates='pr_scan')
    secrets = relationship("Secrets", back_populates="pr_scan")

    scan_type = Column(Enum(PRScanType), default=PRScanType.SECRET, nullable=True)

    vulnerabilities = relationship("Vulnerability", back_populates="pr_scan", cascade="all, delete-orphan")