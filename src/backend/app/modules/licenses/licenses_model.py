from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class License(Base):
    __tablename__ = "licenses"

    id = Column(String, primary_key=True, index=True)
    token = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)