from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum, Float, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.db import Base
from app.modules.vc.models.vc import VcTypes  # Import VcTypes enum


class Repo(Base):
    __tablename__ = 'repositories'

    id = Column(Integer, primary_key=True, index=True)
    vc_id = Column(Integer, ForeignKey('vcs.id'), nullable=False, index=True)
    vctype = Column(Enum(VcTypes), nullable=False, index=True)
    name = Column(String, index=True)
    repoUrl = Column(String, nullable=False)
    author = Column(String, nullable=False)
    other_repo_details = Column(JSON)
    lastScanDate = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)

    secrets = relationship("Secrets", back_populates="repository")
    scans = relationship('RepositoryScan', back_populates='repository')
    pr_scan = relationship('PRScan', back_populates='repository')

    # Relationships
    vc = relationship('VC', back_populates='repositories')
    live_commits = relationship("LiveCommit", back_populates="repository")

    # Foreign keys for properties
    criticality_id = Column(Integer, ForeignKey(
        'business_criticalities.id'), nullable=True)
    environment_id = Column(
        Integer,
        ForeignKey('environments.id'),
        nullable=True)
    sensitivity_id = Column(Integer, ForeignKey(
        'data_sensitivities.id'), nullable=True)
    regulation_id = Column(Integer, ForeignKey(
        'regulatory_requirements.id'), nullable=True)

    # Relationships with the properties
    criticality = relationship('BusinessCriticality', back_populates='repos')
    environment = relationship('Environment', back_populates='repos')
    sensitivity = relationship('DataSensitivity', back_populates='repos')
    regulation = relationship('RegulatoryRequirement', back_populates='repos')

    # Many-to-Many relationship with Group
    groups = relationship(
        'Group',
        secondary='group_repo_association',
        back_populates='repos'
    )

    score_normalized = Column(Float, nullable=True)
    score_normalized_on = Column(DateTime, default=datetime.utcnow)
    sca_branches = Column(ARRAY(String), nullable=True)

    vulnerabilities = relationship("Vulnerability", back_populates="repository")

