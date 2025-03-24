from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db import Base
import enum


class ScanStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class RepoScanType(str, enum.Enum):
    SECRET = 'SECRET'
    VULNERABILITY = 'VULNERABILITY'

class RepositoryScan(Base):
    __tablename__ = 'repository_scans'

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(
        Integer,
        ForeignKey('repositories.id'),
        nullable=False,
        index=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.utcnow())  # Use naive datetime
    status = Column(
        Enum(ScanStatusEnum),
        default=ScanStatusEnum.PENDING,
        nullable=False)

    scan_type = Column(Enum(RepoScanType), default=RepoScanType.SECRET, nullable=True)

    # Relationships
    repository = relationship('Repo', back_populates='scans')
    # secrets = relationship('Secrets', back_populates='repository_scans')

