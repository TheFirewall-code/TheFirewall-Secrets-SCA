from sqlalchemy import Column, Integer, DateTime, String, ARRAY, ForeignKey, Boolean, Table, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db import Base
from app.modules.repository.models.repository import Repo


# Association table for the many-to-many relationship between Group and Repo
group_repo_association = Table(
    'group_repo_association', Base.metadata, Column(
        'group_id', Integer, ForeignKey(
            'groups.id', ondelete="CASCADE"), primary_key=True), Column(
                'repo_id', Integer, ForeignKey(
                    'repositories.id', ondelete="CASCADE"), primary_key=True))


class Group(Base):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    active = Column(Boolean, default=True)

    # Many-to-Many relationship with Repo
    repos = relationship(
        'Repo',
        secondary='group_repo_association',
        back_populates='groups'
    )

    created_on = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=False)

    score_normalized = Column(Float, nullable=True)
    score_normalized_on = Column(DateTime, default=datetime.utcnow)
