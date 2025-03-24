from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

from app.modules.pr.models.pr_scan import PRScanType
from app.modules.pr.schemas.pr_schema import PR


class StatusEnum(str, Enum):
    pending = "pending"
    completed = "completed"
    processing = "processing"
    failed = "failed"


class PRScanBase(BaseModel):
    pr_id: int
    vc_id: int
    webhook_id: int
    repo_id: int
    vc_type: str
    status: StatusEnum = StatusEnum.pending
    block_status: Optional[bool] = True
    other_details: Optional[Dict[str, Any]] = None
    stat_url: Optional[str] = None
    scan_type: Optional[PRScanType]


class PRScanCreate(PRScanBase):
    pass


class PRScanUpdate(BaseModel):
    status: Optional[StatusEnum] = None
    block_status: Optional[bool] = False


class PRScan(PRScanBase):
    id: int
    created_at: datetime
    pr: PR
    vc_name: str
    repo_name: str
    secret_count: int = 0
    vulnerability_count: int = 0
    scan_type: PRScanType

    class Config:
        from_attributes = True
