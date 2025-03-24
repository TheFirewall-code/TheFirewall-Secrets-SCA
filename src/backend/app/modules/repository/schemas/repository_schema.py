from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum
from typing import Dict, List, Any

from app.modules.repository.models import repository
from app.modules.secrets.schema.secret_schema import SecretsResponse
from app.modules.secrets.schema.secret_schema import SeverityLevel

class VCResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    type: str
    url: str
    added_by_user_id: int
    created_by: int
    updated_by: int
    active: bool

    class Config:
        from_attributes = True


class RepoBase(BaseModel):
    name: str
    repoUrl: str
    author: str
    other_repo_details: Optional[Dict] = None
    score_normalized: Optional[float]
    score_normalized_on: Optional[datetime]


class SecretsResponse(BaseModel):
    id: int
    secret: Optional[str] = None
    severity: Optional[SeverityLevel] = None
    description: Optional[str] = None
    file: Optional[str] = None
    line: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    start_column: Optional[int] = None
    end_column: Optional[int] = None
    match: Optional[str] = None
    rule: Optional[str] = None
    commit: Optional[str] = None
    author: Optional[str] = None
    email: Optional[str] = None
    date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    repository_id: Optional[int] = None
    message: Optional[str] = None
    fingerprint: Optional[str] = None
    entropy: Optional[float] = None
    whitelist_id: Optional[int] = None
    whitelisted: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pr_id: Optional[int] = None
    pr_scan_id: Optional[int] = None
    commit_id: Optional[int] = None
    live_commit_id: Optional[int] = None
    live_commit_scan_id: Optional[int] = None
    

    class Config:
        from_attributes = True


class RepoCreate(RepoBase):
    vc_id: int


class RepoUpdate(RepoBase):
    lastScanDate: Optional[datetime] = None


class RepoResponse(RepoBase):
    secrets_count: int
    vulnerability_count: int
    sca_branches: Optional[List[str]] = None
    id: int
    lastScanDate: datetime
    created_at: datetime
    vc: Optional[VCResponse] = None

    class Config:
        from_attributes = True


class RepoId(BaseModel):
    repository_id: int

    class Config:
        from_attributes = True


class FetchReposRequest(BaseModel):
    vc_id: int


class SortByEnum(str, Enum):
    VC_ID = "vc_id"
    REPO_ID = "repo_id"
    SECRETS_COUNT = "secrets_count"
    CREATED_AT = 'created_at'
    SCORE_NORMALIZED = 'score_normalized'
    AUTHOR = 'author'
    VULNERABILITY_COUNT = "vulnerability_count"


class FilterOption(BaseModel):
    key: str
    label: str
    type: str
    searchable: bool


class FilterValueCount(BaseModel):
    value: Any
    count: int
