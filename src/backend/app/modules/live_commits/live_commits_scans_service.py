from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy import func, distinct, update
from typing import List
from sqlalchemy import or_
from sqlalchemy import cast, String

from sqlalchemy.sql import text

from app.modules.live_commits.models.live_commits_scan import LiveCommitScan
from app.modules.live_commits.schemas.live_commits_schemas import LiveCommitScanCreate
from app.utils.pagination import paginate
from app.modules.pr.models.pr_scan import StatusEnum
from app.modules.live_commits.live_commits_service import get_commits_for_scan
from sqlalchemy.orm import joinedload
from app.modules.live_commits.models.live_commits_scan import LiveCommitScanType
from app.modules.secrets.model.secrets_model import Secrets
from app.modules.vulnerability.models.vulnerability_model import Vulnerability
from app.modules.vc.models.vc import VC
from app.modules.repository.models.repository import Repo
from app.modules.live_commits.models.live_commits import LiveCommit
import logging
from sqlalchemy.exc import SQLAlchemyError
logger = logging.getLogger(__name__)

async def add_live_commit_scan(
        db: AsyncSession,
        live_commit_scan: LiveCommitScanCreate):
    new_scan = LiveCommitScan(
        vc_id=live_commit_scan.vc_id,
        webhook_id=live_commit_scan.webhook_id,
        repo_id=live_commit_scan.repo_id,
        status=live_commit_scan.status,
        live_commit_id = live_commit_scan.live_commit_id,
        scan_type = live_commit_scan.scan_type
    )
    print("Adding a new live commit scan in db")
    db.add(new_scan)
    await db.commit()
    await db.refresh(new_scan)
    return new_scan


async def get_live_commits_scan(
    db: AsyncSession,
    vc_ids: List[int] = None,
    repo_ids: List[int] = None,
    commit_ids: List[str] = None,  # commit_ids remains as a list
    author: str = None,  # author_name as a string
    commit_msg: str = None,   # commit_msg as a string
    page: int = 1,
    limit: int = 10,
    live_commit_scan_type: LiveCommitScanType = None,
    search: str = None,
    sort_by: str = None,
    order_by: str = "asc"
):
    # Filters
    filters = []
    if vc_ids:
        filters.append(LiveCommitScan.vc_id.in_(vc_ids))
    if repo_ids:
        filters.append(LiveCommitScan.repo_id.in_(repo_ids))
    if live_commit_scan_type:
        filters.append(LiveCommitScan.scan_type == live_commit_scan_type)
    if commit_ids:
        filters.append(LiveCommit.commit_id.in_(commit_ids))
    if author:
        filters.append(LiveCommit.author_name.ilike(f"%{author}%"))
    if commit_msg:
        filters.append(LiveCommit.commit_msg.ilike(f"%{commit_msg}%"))
    if search:
        search_filter = or_(
            cast(LiveCommitScan.vc_id, String).ilike(f"%{search}%"),
            cast(LiveCommitScan.repo_id, String).ilike(f"%{search}%"),
            cast(LiveCommitScan.scan_type, String).ilike(f"%{search}%"),
            cast(LiveCommitScan.status, String).ilike(f"%{search}%"),
            LiveCommit.commit_id.ilike(f"%{search}%"),
            LiveCommit.commit_msg.ilike(f"%{search}%"),
            LiveCommit.author_name.ilike(f"%{search}%")
        )
        filters.append(search_filter)

    # Subquery for counts
    counts_subquery = (
        select(
            LiveCommitScan.id.label("scan_id"),
            func.count(Secrets.id).label("secret_count"),
            func.count(Vulnerability.id).label("vulnerability_count")
        )
        .outerjoin(Secrets, Secrets.live_commit_scan_id == LiveCommitScan.id)
        .outerjoin(Vulnerability, Vulnerability.live_commit_scan_id == LiveCommitScan.id)
        .group_by(LiveCommitScan.id)
        .subquery()
    )

    # Main query
    query = (
        select(
            LiveCommitScan.id,
            LiveCommitScan.vc_id,
            LiveCommitScan.repo_id,
            VC.name.label("vc_name"),
            Repo.name.label("repo_name"),
            LiveCommit.commit_id,
            LiveCommit.commit_url,
            LiveCommit.author_name,
            LiveCommit.commit_msg,
            LiveCommit.other_details,
            LiveCommitScan.status,
            LiveCommitScan.scan_type,
            counts_subquery.c.secret_count,
            counts_subquery.c.vulnerability_count,
            LiveCommitScan.created_at
        )
        .join(VC, LiveCommitScan.vc_id == VC.id)
        .join(Repo, LiveCommitScan.repo_id == Repo.id)
        .outerjoin(LiveCommit, LiveCommit.id == LiveCommitScan.live_commit_id)
        .outerjoin(counts_subquery, counts_subquery.c.scan_id == LiveCommitScan.id)
        .filter(and_(*filters)) if filters else select(LiveCommitScan)
    )

    # Sorting
    if sort_by in [
        "vc_name",
        "repo_name",
        "secret_count",
        "vulnerability_count",
        "created_at",
        "commit_id"
    ]:
        sort_column = (
            getattr(counts_subquery.c, sort_by)
            if sort_by in ["secret_count", "vulnerability_count"]
            else getattr(LiveCommitScan, sort_by)
            if sort_by == "created_at"
            else VC.name
            if sort_by == "vc_name"
            else Repo.name
            if sort_by == "repo_name"
            else LiveCommit.commit_id
        )
        query = query.order_by(
            sort_column.asc() if order_by == "asc" else sort_column.desc()
        )

    # Total count
    total_count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(total_count_query)

    # Pagination
    result_query = paginate(query, total_count, page, limit)
    result = await db.execute(result_query["query"])
    scans_with_details = [
        {
            "id": row.id,
            "vc_id": row.vc_id,
            "repo_id": row.repo_id,
            "vc_name": row.vc_name,
            "repo_name": row.repo_name,
            "commit_id": row.commit_id,
            "commit_url": row.commit_url,
            "author_name": row.author_name,
            "commit_msg": row.commit_msg,
            "status": row.status,
            "scan_type": row.scan_type,
            "secret_count": row.secret_count,
            "vulnerability_count": row.vulnerability_count,
            "created_at": row.created_at,
        }
        for row in result.all()
    ]

    return {"data": scans_with_details, **result_query["meta"]}



async def get_scan_with_commits(db: AsyncSession, scan_id: int):
    scan_query = select(LiveCommitScan).filter(LiveCommitScan.id == scan_id)
    scan_result = await db.execute(scan_query)
    scan = scan_result.scalar_one_or_none()

    if not scan:
        return None

    commits = await get_commits_for_scan(db, scan.id)
    scan.commits = commits
    return scan


async def update_live_commit_scan_status(
        db: AsyncSession,
        live_commit_scan_id: int,
        status: StatusEnum
    ):
    query = update(LiveCommitScan).where(LiveCommitScan.id == live_commit_scan_id).values(status=status)
    await db.execute(query)
    await db.commit()


async def get_live_commit_scan_filters(db: AsyncSession) -> dict:

    return {
        "filters": [
            {"key": "vc_ids", "label": "Version Control IDs", "type": "api"},
            {"key": "repo_ids", "label": "Repository IDs", "type": "api"},
            {"key": "author", "label": "Author", "type": "text"},
            {"key": "commit_ids", "label": "Commit IDs", "type": "api"},
        ]
    }




async def get_live_commit_scan_filter_values(db: AsyncSession, filter_name: str):
    try:
        # Define the query based on the filter_name
        if filter_name == 'sort_by':
            return ["vc_name", "repo_name", "secret_count", "vulnerability_count", "created_at"]
        elif filter_name == 'order_by':
            return ['desc', 'asc']
        elif filter_name == "vc_ids":
            query = select(distinct(LiveCommitScan.vc_id))
        elif filter_name == "repo_ids":
            query = select(distinct(LiveCommitScan.repo_id))
        elif filter_name == "author":
            query = select(distinct(LiveCommit.author_name))
        elif filter_name == "commit_ids":
            query = (
                select(distinct(LiveCommit.commit_id))
                .join(LiveCommitScan, LiveCommit.id == LiveCommitScan.live_commit_id)
            )
        else:
            logger.error(f"Invalid filter name provided: {filter_name}")
            raise ValueError(f"Invalid filter name: {filter_name}")

        # Execute the query and fetch the results
        result = await db.execute(query)
        rows = result.fetchall()

        # Prepare the return value depending on the filter_name
        if filter_name == "author":
            # For 'author', return a list of dicts with value and label
            return {
                "values": [{"value": row[0], "label": row[0]} for row in rows],
                "total": len(rows)
            }

        # For other filters, return a simple list with the total count
        return {
            "values": [row[0] for row in rows],
            "total": len(rows)
        }

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        raise e
