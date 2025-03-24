from sqlalchemy import Column, String, DateTime, Boolean, func
from app.core.db import Base

class JiraAlert(Base):
    __tablename__ = "jira_alerts"
    
    id = Column(String, primary_key=True, index=True, default="default_alert")
    base_url = Column(String, nullable=False)
    user_email = Column(String, nullable=False)
    project_key = Column(String, nullable=False)
    api_token = Column(String, nullable=False)
    # take what type of issue they want to create on jira, make it optional DEFAULT = 'BUG'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)