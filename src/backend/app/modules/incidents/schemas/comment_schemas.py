from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CommentBase(BaseModel):
    content: str
    incident_id: int

    class Config:
        from_attributes = True


class CommentResponse(CommentBase):
    id: int
    user_id: int = None
    created_at: datetime

    class Config:
        from_attributes = True
