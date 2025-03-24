from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

# Enum for Version Control Types
class VcTypesEnum(str, Enum):
    gitlab = "gitlab"
    github = "github"
    bitbucket = "bitbucket"

# Base schemas for PR
class PRBase(BaseModel):
    pr_id: int
    pr_name: Optional[str]
    repo_id: int
    pr_link: str
    vctype: VcTypesEnum
    vc_id: int
    webhook_id: int
    last_scan: Optional[datetime] = None
    secret_count: Optional[int] = None
    vulnerability_count: Optional[int] = None

# Schema for creating a new PR
class PRCreate(BaseModel):
    pr_id: int
    pr_name: Optional[str]
    repo_id: int
    pr_link: str
    vctype: VcTypesEnum
    vc_id: int
    webhook_id: int
    last_scan: Optional[datetime] = None

# Schema for updating an existing PR
class PRUpdate(BaseModel):
    pr_name: Optional[str]
    last_scan: Optional[datetime]

# Base schemas for PR in the database
class PRInDBBase(PRBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Updated for Pydantic v2

# Schema for returning a PR
class PR(PRInDBBase):
    pass

# Schema for PR as stored in the database
class PRInDB(PRInDBBase):
    pass
