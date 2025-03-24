from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class VcTypes(str, Enum):
    bitbucket = "bitbucket"
    github = "github"
    gitlab = "gitlab"

class AllowedScanType(str, Enum):
    loose = "Loose"
    aggressive = "Aggressive"

class WebhookActions(str, Enum):
    pr_opened = 'pr_opened',
    pr_updated = 'pr_updated',
    commit_push = 'commit_push',
    repo_push = 'repo_push'

class WebhookConfigBase(BaseModel):
    vc_id: int
    vc_type: VcTypes
    scan_type: Optional[AllowedScanType] = None
    git_actions: Optional[List[str]] = None
    target_repos: Optional[List[str]] = None
    block_message: Optional[str] = None
    unblock_message: Optional[str] = None
    active: bool = True
    block_pr_on_sec_found: bool = True
    block_pr_on_vul_found: bool = False
    jira_alerts_enabled: bool = True
    slack_alerts_enabled: bool = True

class WebhookConfigCreate(WebhookConfigBase):
    pass

class WebhookConfigUpdate(WebhookConfigBase):
    pass

class WebhookConfigDetail(WebhookConfigBase):
    id: int
    secret: str
    url: Optional[str]

class WebhookConfigResponse(BaseModel):
    id: int
    vc_type: str
    webhook_url: Optional[str] = None
    secret: str
    message: str
    active: bool
    block_message: Optional[str] = None
    unblock_message: Optional[str] = None
    block_pr_on_sec_found: bool
    block_pr_on_vul_found: bool
    jira_alerts_enabled: bool
    slack_alerts_enabled: bool
