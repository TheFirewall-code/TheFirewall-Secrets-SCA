from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import distinct

from sqlalchemy import select, func, cast, Integer, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.modules.pr.models.pr import PR as models_PR
from app.modules.pr.schemas.pr_schema import PRCreate, PRUpdate, PR, PRInDB
from app.utils.pagination import paginate
from app.modules.secrets.model.secrets_model import Secrets
from app.modules.vulnerability.models.vulnerability_model import Vulnerability
from fastapi import HTTPException

def to_int(value):
    try:
        return int(value)
    except ValueError:
        return None

async def create_pr(db: AsyncSession, pr: PRCreate) -> models_PR:
    query = select(models_PR).where(
        models_PR.pr_id == pr.pr_id,
        models_PR.vc_id == pr.vc_id,
        models_PR.repo_id == pr.repo_id
    )
    existing_pr = (await db.execute(query)).scalar_one_or_none()

    if existing_pr:
        return existing_pr

    db_pr = models_PR(**pr.dict())
    db.add(db_pr)
    await db.commit()
    await db.refresh(db_pr)
    return db_pr


async def get_pr(
    db: AsyncSession,
    pr_id: Optional[int] = None,
    vc_ids: Optional[List[int]] = None,
    repo_ids: Optional[List[int]] = None,
    pr_name: Optional[str] = None, 
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> dict:
    # Base query for PRs with counts of secrets and vulnerabilities
    secret_count_subq = (
        select(Secrets.pr_id, func.count(Secrets.id).label("secret_count"))
        .group_by(Secrets.pr_id)
        .subquery()
    )

    vulnerability_count_subq = (
        select(Vulnerability.pr_id, func.count(Vulnerability.id).label("vulnerability_count"))
        .group_by(Vulnerability.pr_id)
        .subquery()
    )

    # Join the subqueries to the main PR query
    query = (
        select(models_PR, func.coalesce(secret_count_subq.c.secret_count, 0).label("secret_count"),
               func.coalesce(vulnerability_count_subq.c.vulnerability_count, 0).label("vulnerability_count"))
        .outerjoin(secret_count_subq, models_PR.id == secret_count_subq.c.pr_id)
        .outerjoin(vulnerability_count_subq, models_PR.id == vulnerability_count_subq.c.pr_id)
    )

    # Add filters
    if pr_id:
        query = query.where(models_PR.pr_id == pr_id)
    if vc_ids:
        query = query.where(models_PR.vc_id.in_(vc_ids))
    if repo_ids:
        query = query.where(models_PR.repo_id.in_(repo_ids))
    if pr_name:
        query = query.where(models_PR.pr_name.ilike(f"%{pr_name}%"))
    if search:
        # Try to convert search to integer for numeric fields; use as string for others
        search_int = to_int(search)
        query = query.where(
            or_(
                models_PR.pr_name.ilike(f"%{search}%"),
                models_PR.pr_id == search_int if search_int is not None else None,
                models_PR.vc_id == search_int if search_int is not None else None,
                models_PR.repo_id == search_int if search_int is not None else None,
            )
        )

    # Pagination and execution
    total_count = await db.scalar(select(func.count()).select_from(query.subquery()))
    result_query = paginate(query, total_count, page, limit)
    prs = (await db.execute(result_query['query'])).all()

    data = [
        {
            "pr": PR.from_orm(pr[0]),
            "secret_count": pr[1],
            "vulnerability_count": pr[2]
        }
        for pr in prs
    ]

    return {"data": data, **result_query['meta']}






async def get_pr_by_id(db: AsyncSession, pr_id: int) -> PRInDB:
    db_pr = (await db.execute(select(models_PR).where(models_PR.id == pr_id))).scalar_one_or_none()

    if not db_pr:
        raise HTTPException(status_code=404, detail="PR not found")

    return db_pr


async def update_pr_blocked_status(
        db: AsyncSession,
        pr_id: int,
        blocked: bool) -> models_PR:
    db_pr = (await db.execute(select(models_PR).where(models_PR.id == pr_id))).scalar_one_or_none()

    if not db_pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PR not found")

    db_pr.blocked = blocked
    await db.commit()
    await db.refresh(db_pr)
    return db_pr


async def get_pr_blocked_status(db: AsyncSession, pr_id: int) -> bool:
    return (await db.execute(select(models_PR.blocked).where(models_PR.id == pr_id))).scalar()


async def get_available_filters() -> dict:
    return {
        "filters": [
            {"key": "vc_ids", "label": "VCs", "type": "api"},
            {"key": "repo_ids", "label": "Repositories", "type": "api"},
            {"key": "pr_name", "label": "PR Name", "type": "text"},
        ]
    }


async def get_filter_values(db: AsyncSession, filter_name: str) -> List:
    filter_map = {
        "vc_ids": models_PR.vc_id,
        "repo_ids": models_PR.repo_id,
        "pr_name": models_PR.pr_name
    }

    if filter_name not in filter_map:
        raise HTTPException(status_code=400, detail="Invalid filter name")

    values = (await db.execute(select(distinct(filter_map[filter_name])))).scalars().all()
    return values
