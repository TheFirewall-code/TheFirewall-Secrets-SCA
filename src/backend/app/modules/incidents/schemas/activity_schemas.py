from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum
from app.modules.incidents.models.incident_model import IncidentStatusEnum
from app.modules.incidents.models.activity_model import Action


class ActivityBase(BaseModel):
    action: Action
    old_value: str = None
    new_value: str = None


class ActivityUpdate(ActivityBase):
    action: Optional[str] = None
    old_value: Optional[IncidentStatusEnum] = None
    new_value: Optional[IncidentStatusEnum] = None


class ActivityCreate(ActivityBase):
    incident_id: int
    user_id: Optional[int] = None
    comment_id: Optional[int] = None


class ActivityResponse(ActivityBase):
    id: int
    created_at: datetime
    incident_id: int
    user_id: Optional[int] = None
    comment_id: Optional[int] = None

    class Config:
        from_attributes = True
