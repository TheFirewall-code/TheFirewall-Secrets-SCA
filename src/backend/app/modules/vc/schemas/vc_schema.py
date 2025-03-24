from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
import enum


class VcTypes(str, enum.Enum):
    bitbucket = "bitbucket"
    github = "github"
    gitlab = "gitlab"


class VCBase(BaseModel):
    type: VcTypes
    token: str
    url: str


class VCCreate(VCBase):
    name: str
    description: Optional[str] = None


class VCResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    type: str
    token: str
    url: str
    added_by_user_id: int
    created_by: int
    updated_by: int
    active: bool

    class Config:
        from_attributes = True


class VCUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    token: Optional[str] = None
    url: Optional[str] = None
    active: Optional[bool] = None

    class Config:
        from_attributes = True
