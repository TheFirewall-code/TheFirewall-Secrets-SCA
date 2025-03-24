from pydantic import BaseModel
from typing import Optional

# Base model for shared attributes


class SlackIntegrationBase(BaseModel):
    token: Optional[str] = None
    channel: Optional[str] = None
    active: Optional[bool] = True

    class Config:
        from_attributes = True


class CreateSlackIntegration(SlackIntegrationBase):
    token: str
    channel: str


class UpdateSlackIntegration(SlackIntegrationBase):
    pass
