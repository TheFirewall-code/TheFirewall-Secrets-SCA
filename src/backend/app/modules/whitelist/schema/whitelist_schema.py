from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Enum to match WhitelistType in SQLAlchemy model
from enum import Enum

class WhiteListType(str, Enum):
    SECRET = "SECRET"
    VULNERABILITY = "VULNERABILITY"

# Base schemas for Whitelist
class WhitelistBase(BaseModel):
    type: WhiteListType
    name: str
    active: bool = True
    global_: bool = False
    repos: Optional[List[int]] = None
    vcs: List[int]
    comments: Optional[List[int]] = None

# Schema for creating a whitelist
class WhitelistCreate(BaseModel):
    type: WhiteListType
    name: Optional[str] = None
    active: bool = True
    global_: bool = False
    repos: Optional[List[int]] = None
    vcs: List[int] = []
    comment: Optional[str] = None

# Schema for updating a whitelist
class WhitelistUpdate(BaseModel):
    type: Optional[WhiteListType] = None
    name: Optional[str] = None
    active: Optional[bool] = None
    global_: Optional[bool] = None
    repos: Optional[List[int]] = None
    vcs: Optional[List[int]] = None
    comment: Optional[str] = None

class VCSInfo(BaseModel):
    id: int
    name: str

class RepoInfo(BaseModel):
    id: int
    name: str

# Base schemas for comments
class WhitelistCommentBase(BaseModel):
    comment: str

class WhitelistCommentCreate(WhitelistCommentBase):
    created_by: int

class WhitelistCommentResponse(WhitelistCommentBase):
    id: int
    created_by: str
    user_id: int
    comment: str
    created_on: datetime

    class Config:
        from_attributes = True



class WhitelistResponse(BaseModel):
    id: int
    type: WhiteListType
    name: Optional[str]
    active: bool = True
    global_: bool = False
    created_on: datetime
    vcs: Optional[List[VCSInfo]] = []
    repos: Optional[List[RepoInfo]] = []
    comments: Optional[List[WhitelistCommentResponse]] = []

    class Config:
        from_attributes = True


class WhitelistUpdateResponse(BaseModel):
    id: int
    name: Optional[str] = ""
    created_by: int
    updated_by: int
    secrets_updated: Optional[int] = None
    vulnerabilities_updated: Optional[int] = None
    created_on: datetime
    comments: Optional[List[int]] = []
    type: Optional[str] = ""
    class Config:
        from_attributes = True
