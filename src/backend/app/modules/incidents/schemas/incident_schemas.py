from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum
from app.modules.incidents.models.incident_model import IncidentStatusEnum, IncidentTypeEnum, IncidentClosedBy
from app.modules.secrets.model.secrets_model import ScanType, SeverityLevel
from fastapi import Query
from app.modules.secrets.schema.secret_schema import SecretsResponse
from app.modules.vulnerability.models.vulnerability_model import VulnerabilityType


# Base Incident schemas
class IncidentBase(BaseModel):
    name: str
    type: Optional[IncidentTypeEnum] = IncidentTypeEnum.secret
    status: IncidentStatusEnum = IncidentStatusEnum.OPEN
    closed_by: IncidentClosedBy = IncidentClosedBy.USER
    secret_id: Optional[int] = None
    vulnerability_id: Optional[int] = None

# Schema for creating/updating an Incident


class IncidentUpdate(BaseModel):
    type: Optional[IncidentTypeEnum]
    updated_at: datetime = datetime.utcnow()

# Response schemas for an Incident


class IncidentResponse(IncidentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    secret: SecretsResponse

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

# Enums from your codebase
class IncidentTypeEnum(str, Enum):
    secret = "secret"
    vulnerability = "vulnerability"


class IncidentFilters(BaseModel):
    """
    Filters for searching/incidents.
    Includes both common fields, secret-specific, and vulnerability-specific.
    """

    # -------------------------
    # Common incident filters
    # -------------------------
    # Now allow multiple statuses
    statuses: Optional[List[IncidentStatusEnum]] = None

    incident_type: Optional[IncidentTypeEnum] = None  # 'secret' or 'vulnerability'
    search: Optional[str] = None

    # Date/time filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None

    # -------------------------
    # Secret-specific filters
    # -------------------------
    # Examples of multi: rule, commit, author, email, etc.
    # Adjust as needed.
    secrets: Optional[List[str]] = None
    rules: Optional[List[str]] = None
    commits: Optional[List[str]] = None
    authors: Optional[List[str]] = None
    emails: Optional[List[str]] = None
    descriptions: Optional[List[str]] = None

    # You can still keep single booleans or ints if you prefer:
    pr_scan_id: Optional[int] = None
    whitelisted: Optional[bool] = None

    # severity as a multi-list if you want multiple severities:
    severities: Optional[List[str]] = None

    scan_types: Optional[List[str]] = None
    messages: Optional[List[str]] = None
    branches: Optional[List[str]] = None

    # -------------------------
    # Vulnerability-specific filters
    # -------------------------
    vulnerability_ids: Optional[List[str]] = None
    cve_ids: Optional[List[str]] = None
    packages: Optional[List[str]] = None
    package_versions: Optional[List[str]] = None
    fix_available: Optional[bool] = None
    artifact_types: Optional[List[str]] = None
    artifact_paths: Optional[List[str]] = None
    vulnerability_types: Optional[List[VulnerabilityType]] = None
    licenses: Optional[List[str]] = None


class IncidentFetchParams(IncidentFilters):
    repo_ids: Optional[List[int]] = None
    vc_ids: Optional[List[int]] = None
    pr_ids: Optional[List[int]] = None
    group_ids: Optional[List[int]] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    page: int = 1
    limit: int = 10
    sort_by: str = "created_at"
    order_by: str = "desc"

class BulkIncidentUpdate(BaseModel):
    status: Optional[IncidentStatusEnum]


class BulkIncidentUpdateByIds(BulkIncidentUpdate):
    incident_ids: List[int]


class BulkIncidentUpdateByFilters(BulkIncidentUpdate):
    filters: IncidentFilters
