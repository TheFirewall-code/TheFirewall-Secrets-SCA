from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class JiraAlertBase(BaseModel):
    base_url: str
    user_email: str
    api_token: str
    project_key: str
    is_active: bool

class JiraAlertCreate(JiraAlertBase):
    pass

class JiraAlertResponse(JiraAlertBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    

    class Config:
        from_attributes = True
