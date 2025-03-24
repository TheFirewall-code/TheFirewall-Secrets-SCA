from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func, asc, desc, distinct
from sqlalchemy.orm import joinedload
from typing import List

from app.modules.vc.models.vc import VC
from app.modules.repository.models.repository import Repo
from app.modules.live_commits.models.live_commits import LiveCommit
from app.modules.live_commits.schemas.live_commits_schemas import LiveCommitCreate
from app.utils.pagination import paginate


async def add_live_commit(db: AsyncSession, live_commit: LiveCommitCreate):
    # Check if the commit already exists
    query = select(LiveCommit).where(
        LiveCommit.vc_id == live_commit.vc_id,
        LiveCommit.repo_id == live_commit.repo_id,
        LiveCommit.commit_id == live_commit.commit_id,
    )
    result = await db.execute(query)
    existing_commit = result.scalars().first()

    if existing_commit:
        return existing_commit

    new_commit = LiveCommit(
        vc_id=live_commit.vc_id,
        repo_id=live_commit.repo_id,
        branch=live_commit.branch,
        commit_id=live_commit.commit_id,
        commit_url=live_commit.commit_url,
        author_name=live_commit.author_name,
        commit_msg=live_commit.commit_msg,
        other_details=live_commit.other_details,
    )
    db.add(new_commit)
    await db.commit()
    await db.refresh(new_commit)
    return new_commit


async def get_live_commits(
    db: AsyncSession,
    vc_ids: List[int] = None,
    repo_ids: List[int] = None,
    branch_name: str = None,
    sort_by: str = None,
    order_by: str = None,
    page: int = 1,
    limit: int = 10
):
    filters = []
    if vc_ids:
        filters.append(LiveCommit.vc_id.in_(vc_ids))
    if repo_ids:
        filters.append(LiveCommit.repo_id.in_(repo_ids))
    if branch_name:
        filters.append(LiveCommit.branch == branch_name)

    query = (
        select(
            LiveCommit,
            VC.name.label('vc_name'),
            Repo.name.label('repo_name')) .join(
            LiveCommit.vc) .join(
                LiveCommit.repository) .options(
                    joinedload(
                        LiveCommit.vc),
            joinedload(
                        LiveCommit.repository)))

    order = asc if order_by == "asc" else desc
    if sort_by == "created_at":
        query = query.order_by(order(LiveCommit.created_at))

    if filters:
        query = query.filter(and_(*filters))

    total_count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(total_count_query)

    result_query = paginate(query, total_count, page, limit)
    result = await db.execute(result_query['query'])
    commits = result.scalars().all()

    return {"data": commits, **result_query['meta']}


async def get_commits_for_scan(db: AsyncSession, live_commit_scan_id: int):
    query = select(LiveCommit).filter(
        LiveCommit.live_commit_scan_id == live_commit_scan_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_live_commit_filters(db: AsyncSession) -> dict:
    return {
        "filters": [
            {"key": "vc_ids", "label": "Version Control IDs", "type": "api"},
            {"key": "repo_ids", "label": "Repository IDs", "type": "api"},
            {"key": "branch_name", "label": "Branch Names", "type": "text"},
        ]
    }


async def get_live_commit_filter_values(db: AsyncSession, filter_name: str):
    if filter_name == "vc_ids":
        query = select(distinct(LiveCommit.vc_id))
    elif filter_name == "repo_ids":
        query = select(distinct(LiveCommit.repo_id))
    elif filter_name == "branch_name":
        query = select(distinct(LiveCommit.branch))
    else:
        raise ValueError("Invalid filter name")

    result = await db.execute(query)
    return [row[0] for row in result.fetchall()]