from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db import Base


class BusinessCriticality(Base):
    __tablename__ = 'business_criticalities'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(Float, nullable=False)

    created_by = Column(Integer, nullable=False, default=-1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, nullable=True, default=-1)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)

    repos = relationship('Repo', back_populates='criticality')


class Environment(Base):
    __tablename__ = 'environments'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(Float, nullable=False)

    created_by = Column(Integer, nullable=False, default=-1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, nullable=True, default=-1)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)

    repos = relationship('Repo', back_populates='environment')


class DataSensitivity(Base):
    __tablename__ = 'data_sensitivities'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(Float, nullable=False)

    created_by = Column(Integer, nullable=False, default=-1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, nullable=True, default=-1)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)

    repos = relationship('Repo', back_populates='sensitivity')


class RegulatoryRequirement(Base):
    __tablename__ = 'regulatory_requirements'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(Float, nullable=False)

    created_by = Column(Integer, nullable=False, default=-1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, nullable=True, default=-1)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)

    repos = relationship('Repo', back_populates='regulation')
