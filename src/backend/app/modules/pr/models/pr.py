from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, Enum, UniqueConstraint, Boolean
from datetime import datetime, timezone
from app.modules.vc.models.vc import VcTypes
from app.core.db import Base
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship


class PR(Base):
    __tablename__ = 'prs'

    id = Column(Integer, primary_key=True, index=True)
    pr_id = Column(Integer, nullable=False)
    pr_name = Column(String, nullable=True)

    repo_id = Column(Integer, ForeignKey('repositories.id'), nullable=False)
    pr_link = Column(String, nullable=False)

    vctype = Column(Enum(VcTypes), nullable=False)
    vc_id = Column(Integer, nullable=False)

    webhook_id = Column(
        Integer,
        ForeignKey('webhook_configs.id'),
        nullable=False)

    created_at = Column(
        TIMESTAMP(
            timezone=True),
        nullable=False,
        default=lambda: datetime.now(
            timezone.utc))
    last_scan = Column(TIMESTAMP(timezone=True), nullable=True)

    blocked = Column(Boolean, nullable=False, server_default='false')

    scans = relationship('PRScan', back_populates='pr')
    secrets = relationship('Secrets', back_populates='pr', cascade="all, delete-orphan")
    vulnerabilities = relationship('Vulnerability', back_populates='pr', cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('pr_id', 'vc_id', 'repo_id', name='uq_pr_vc_repo'),
    )
