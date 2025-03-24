from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# Base schemas shared by create and update schemas
class GroupBaseSchema(BaseModel):
    name: str = Field(..., example="DevOps Team")
    description: Optional[str] = Field(
        None, example="Group responsible for DevOps tasks")
    repos: List[int] = Field(default_factory=list, example=[1, 2, 3])


# Create schemas for group creation
class CreateGroupSchema(GroupBaseSchema):
    pass


class ReposRequest(BaseModel):
    repo_ids: List[int] = Field(..., example=[1, 2, 3])


class GroupUpdateRequest(BaseModel):
    """Schema for updating a group."""
    name: Optional[str] = Field(None, title="Group Name", max_length=100)
    description: Optional[str] = Field(None, title="Group Description", max_length=255)
    repos: Optional[List[int]] = Field(None, title="Repository IDs")  # Add repo_ids field


class RepoFilterSchema(BaseModel):
    name: Optional[str] = None
    author: Optional[str] = None
    vc_id: Optional[int] = None
