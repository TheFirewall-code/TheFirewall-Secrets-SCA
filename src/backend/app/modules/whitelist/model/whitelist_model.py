from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, ARRAY, DateTime, func, Enum
from sqlalchemy.ext.declarative import declarative_base
from app.core.db import Base
from datetime import datetime
import enum
from sqlalchemy.orm import relationship


# Enum for WhiteListType
class WhiteListType(enum.Enum):
    SECRET = "SECRET"
    VULNERABILITY = "VULNERABILITY"

class Whitelist(Base):
    __tablename__ = 'whitelist'

    type = Column(Enum(WhiteListType), nullable=False)
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    global_ = Column(Boolean, nullable=False, default=False)
    
    # Repo as an array of integers
    repos = Column(ARRAY(Integer), nullable=True)
    
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False) 
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=True, default=1)
    
    # Comments as int array relation, linked to comment ids
    comments = Column(ARRAY(Integer), nullable=True)
    
    created_on = Column(DateTime, nullable=False, default=func.now())
    
    # vcs as an int array
    vcs = Column(ARRAY(Integer), nullable=False)
    
    def __repr__(self):
        return (
            f"<Whitelist(id={self.id}, "
            f"type={self.type}, "
            f"active={self.active}, "
            f"global_={self.global_}, "
            f"repos={self.repos})>"
        )

class WhitelistComment(Base):
    __tablename__ = 'whitelist_comments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    comment = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_on = Column(DateTime,   default=datetime.utcnow)

    user = relationship("User", back_populates="comments")

    def __repr__(self):
        return (
            f"<WhitelistComment(id={self.id}, "
            f"comment={self.comment}, "
            f"created_by={self.created_by})>"
        )