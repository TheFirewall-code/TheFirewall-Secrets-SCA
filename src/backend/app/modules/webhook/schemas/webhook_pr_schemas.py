from pydantic import BaseModel, root_validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class GithubPR(BaseModel):
    action: Optional[str] = None
    number: Optional[int] = None
    pull_request: Dict[str, Any] = None
    repository: Dict[str, Any]
    sender: Optional[Dict[str, Any]] = None


class BitbucketPR(BaseModel):
    repository: Dict[str, Any]
    pullrequest: Dict[str, Any]
    state: Optional[str] = None

    @root_validator(pre=True)
    def extract_state(cls, values):
        pullrequest = values.get('pullrequest', {})
        values['state'] = pullrequest.get('state')
        return values


class GitlabPR(BaseModel):
    repository: Dict[str, Any]
    project: Dict[str, Any]
    object_attributes: Dict[str, Any]
    state: Optional[str] = None
    action: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None

    @root_validator(pre=True)
    def extract_state_and_action(cls, values):
        object_attributes = values.get('object_attributes', {})
        values['state'] = object_attributes.get('state')
        values['action'] = object_attributes.get('action')
        return values
