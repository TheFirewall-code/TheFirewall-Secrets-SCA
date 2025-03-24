from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict
from datetime import datetime

# GitHub Schema


class GitHubCommit(BaseModel):
    id: str
    message: str
    timestamp: datetime


class GitHubRepository(BaseModel):
    id: int
    name: str
    url: HttpUrl


class GitHubPushPayload(BaseModel):
    action: str = "push"
    ref: str
    commits: List[GitHubCommit]
    repository: GitHubRepository

    def get_head_commit(self):
        return self.commits[-1] if self.commits else None


# Bitbucket Schema
class BitbucketCommit(BaseModel):
    hash: str
    message: str
    date: datetime


class BitbucketRepository(BaseModel):
    uuid: str
    name: str
    links: dict


class BitbucketPushPayload(BaseModel):
    action: str = "push"
    changes: List[BitbucketCommit]

    def get_head_commit(self):
        return self.changes[-1] if self.changes else None


class GitLabCommit(BaseModel):
    id: str
    message: str
    title: str
    timestamp: datetime
    url: HttpUrl


class GitLabProject(BaseModel):
    id: int
    name: str
    namespace: str
    path_with_namespace: str
    default_branch: str
    web_url: HttpUrl
    homepage: HttpUrl
    http_url: HttpUrl


class GitLabRepo(BaseModel):
    name: str
    url: str
    git_http_url: HttpUrl


class GitLabPushPayload(BaseModel):
    before: str
    after: str
    ref: str
    commits: List[GitLabCommit]
    repository: GitLabRepo
    project: GitLabProject

    def get_head_commit(self) -> Optional[GitLabCommit]:
        return self.commits[-1] if self.commits else None

    def get_head_commit(self) -> Optional[GitLabCommit]:
        return self.commits[-1] if self.commits else None
