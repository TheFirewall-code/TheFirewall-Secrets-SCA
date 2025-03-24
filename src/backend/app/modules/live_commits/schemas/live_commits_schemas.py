from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
from app.modules.vc.models.vc import VcTypes
from app.modules.live_commits.models.live_commits_scan import StatusEnum, LiveCommitScanType

class LiveCommitBase(BaseModel):
    vc_id: int
    repo_id: int
    branch: str
    commit_id: str
    commit_url: str
    author_name: str
    commit_msg: str
    other_details: Optional[Dict] = None


class LiveCommitCreate(LiveCommitBase):
    pass


class LiveCommit(LiveCommitBase):
    id: int
    created_at: datetime
    vc_name: str
    repo_name: str

    class Config:
        from_attributes = True

# Live Commit Scan Schemas


class LiveCommitScanBase(BaseModel):
    vc_id: int
    webhook_id: int
    repo_id: int
    status: StatusEnum = StatusEnum.pending
    scan_type: Optional[LiveCommitScanType] = None
    live_commit_id: int


class LiveCommitScanCreate(LiveCommitScanBase):
    pass


class LiveCommitScan(LiveCommitScanBase):
    id: int
    created_at: datetime 

    class Config:
        from_attributes = True


class LiveCommitScanOut(BaseModel):
    id: int
    vc_id: int
    repo_id: int
    status: StatusEnum
    scan_type: Optional[LiveCommitScanType] = None
    secret_count: int
    vulnerability_count: int
    created_at: datetime
    commits: List[LiveCommit] = []

    class Config:
        from_attributes = True
