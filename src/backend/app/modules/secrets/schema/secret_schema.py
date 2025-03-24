from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
from fastapi import Query
from app.utils.pagination import Pagination
from app.modules.secrets.model.secrets_model import ScanType, SeverityLevel
from typing import Dict


class RepoResponse(BaseModel):
    id: int
    name: str
    repoUrl: str
    author: str
    lastScanDate: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SecretsBase(BaseModel):
    secret: str
    description: str
    file: str
    line: str
    start_line: int
    end_line: int
    start_column: int
    end_column: int
    match: str
    rule: str
    commit: str
    author: str
    email: str
    date: datetime
    tags: Optional[List[str]] = None
    repository_id: int
    message: Optional[str]
    fingerprint: Optional[str]
    entropy: Optional[float]
    severity: SeverityLevel
    scan_type: ScanType
    whitelisted: bool  # New field for whitelisted


class SecretsCreate(SecretsBase):
    pass


class SecretsUpdate(BaseModel):
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
    message: Optional[str] = None
    fingerprint: Optional[str] = None
    entropy: Optional[float] = None
    severity: Optional[SeverityLevel] = None
    scan_type: Optional[ScanType] = None
    whitelist_id: Optional[int] = None
    whitelisted: Optional[bool] = None


class SecretsResponse(SecretsBase):
    id: int
    secret: Optional[str] = None
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
    severity: Optional[SeverityLevel] = None
    scan_type: Optional[ScanType] = None
    whitelist_id: Optional[int] = None
    whitelisted: Optional[bool] = None  # New field for whitelisted
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pr_id: Optional[int] = None
    pr_scan_id: Optional[int] = None
    commit_id: Optional[int] = None
    live_commit_id: Optional[int] = None
    live_commit_scan_id: Optional[int] = None
    repository: Optional[RepoResponse] = None

    class Config:
        from_attributes = True


class SecretsResponsePagniation(Pagination):
    data: SecretsResponse


class FilterValueResponse(BaseModel):
    values: List[Dict[str, str]]  # Change to accept a list of dictionaries
    total: int


class GetSecretsRequest(BaseModel):
    # Common
    search: Optional[str] = None

    # Identifiers for scans (if applicable)
    pr_scan_id: Optional[int] = None
    commit_scan_id: Optional[int] = None

    # Secret-specific filters (all multi-select as lists)
    secrets: Optional[List[str]] = None
    rules: Optional[List[str]] = None
    commits: Optional[List[str]] = None
    authors: Optional[List[str]] = None
    emails: Optional[List[str]] = None
    descriptions: Optional[List[str]] = None

    # Boolean filter
    whitelisted: Optional[bool] = None

    # Multi-select enumerated filters
    # If using single value, change the type accordingly. Here we assume a list for multi-select.
    severities: Optional[List[SeverityLevel]] = None
    scan_types: Optional[List[ScanType]] = None
    messages: Optional[List[str]] = None

    # Additional filter (e.g. branch) as multi-select if needed
    branch: Optional[List[str]] = None

    # Date/time filters (kept as singular)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

    # Additional filters for IDs (if required)
    repo_ids: Optional[List[int]] = None
    vc_ids: Optional[List[int]] = None
    pr_ids: Optional[List[int]] = None

    # Pagination and sorting
    page: int = 1
    limit: int = 10
    sort_by: Optional[str] = "repo_count"  # e.g. "repo_count", "secrets", "rules"
    order_by: Optional[str] = "asc"  # "asc" or "desc"