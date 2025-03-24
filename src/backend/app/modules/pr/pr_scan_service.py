from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import asc, desc, select, or_, func, distinct, cast, nullslast
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
from typing import Optional, List
from app.modules.pr.models.pr_scan import PRScan as models_PRScan, StatusEnum
from app.modules.pr.schemas.pr_scan_schema import PRScanCreate, PRScanUpdate, PRScan, PRScanType
from app.utils.pagination import paginate
from app.modules.secrets.model.secrets_model import Secrets
from app.modules.vulnerability.models.vulnerability_model import Vulnerability
from sqlalchemy import String, TEXT
from app.modules.repository.models.repository import Repo
from sqlalchemy.sql import text
from sqlalchemy.sql import literal_column
from app.modules.pr.models.pr import PR

async def create_pr_scan(db: AsyncSession, pr_scan_data: PRScanCreate) -> models_PRScan:
    pr_scan = models_PRScan(**pr_scan_data.dict())
    db.add(pr_scan)
    await db.commit()
    await db.refresh(pr_scan)
    return pr_scan

async def get_pr_scan(
    db: AsyncSession,
    pr_scan_id: Optional[int] = None,
    pr_id: Optional[int] = None,
    repo_ids: Optional[List[int]] = None,
    webhook_id: Optional[int] = None,
    vc_ids: Optional[List[int]] = None,
    status: Optional[bool] = False,
    scan_type: Optional[PRScanType] = None,
    page: int = 1,
    limit: int = 10,
    sort_by: Optional[str] = "created_at",
    order_by: Optional[str] = "desc",
    search: Optional[str] = None  # New search parameter
) -> dict:
    # Subqueries for secret and vulnerability counts
    # Subqueries for secret and vulnerability counts
    secret_count_subquery = (
        select(
            models_PRScan.id.label("pr_scan_id"),  # PRScan ID to link with scans
            func.count(Secrets.id).label("secret_count")  # Count secrets for the PR
        )
        .join(PR, models_PRScan.pr_id == PR.id)  # Join PRScan with PR using pr_id
        .outerjoin(Secrets, Secrets.pr_id == PR.id)  # Join Secrets with PR using pr_id
        .group_by(models_PRScan.id)  # Group by PRScan ID to reflect count for each scan
        .subquery()
    )

    vulnerability_count_subquery = (
        select(
            models_PRScan.id.label("pr_scan_id"),  # PRScan ID to link with scans
            func.count(Vulnerability.id).label("vulnerability_count")  # Count vulnerabilities for the PR
        )
        .join(PR, models_PRScan.pr_id == PR.id)  # Join PRScan with PR using pr_id
        .outerjoin(Vulnerability, Vulnerability.pr_id == PR.id)  # Join Vulnerability with PR using pr_id
        .group_by(models_PRScan.id)  # Group by PRScan ID to reflect count for each scan
        .subquery()
    )

    # Main query with joins and optional filters
    query = (
        select(
            models_PRScan,  # Select PRScan records
            func.coalesce(secret_count_subquery.c.secret_count, 0).label("secret_count"),  # Add secret count
            func.coalesce(vulnerability_count_subquery.c.vulnerability_count, 0).label("vulnerability_count")
            # Add vulnerability count
        )
        .outerjoin(secret_count_subquery,
                   secret_count_subquery.c.pr_scan_id == models_PRScan.id)  # Join secret subquery on PRScan ID
        .outerjoin(vulnerability_count_subquery,
                   vulnerability_count_subquery.c.pr_scan_id == models_PRScan.id)  # Join vulnerability subquery on PRScan ID
        .join(Repo, models_PRScan.repo_id == Repo.id)  # Ensure the repositories table is joined
        .options(
            joinedload(models_PRScan.pr),  # Load PR relationship
            joinedload(models_PRScan.repository),  # Load repository relationship
            joinedload(models_PRScan.vc)  # Load VC relationship
        )
    )

    # Apply filters
    filters = {
        models_PRScan.id: pr_scan_id,
        models_PRScan.pr_id: pr_id,
        models_PRScan.webhook_id: webhook_id,
        models_PRScan.scan_type: scan_type,
    }
    for column, value in filters.items():
        if value is not None:
            query = query.where(column == value)
    if repo_ids:
        query = query.where(models_PRScan.repo_id.in_(repo_ids))
    if vc_ids:
        query = query.where(models_PRScan.vc_id.in_(vc_ids))

    # Search filter across multiple fields
    if search:
        search_filter = or_(
            cast(models_PRScan.id, TEXT).ilike(f"%{search}%"),
            cast(models_PRScan.pr_id, TEXT).ilike(f"%{search}%"),
            cast(models_PRScan.repo_id, TEXT).ilike(f"%{search}%"),
            cast(models_PRScan.vc_id, TEXT).ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    # Sorting
    order = asc if order_by == "asc" else desc
    sort_columns = {
        "repo_name": Repo.name,
        "pr_id": models_PRScan.pr_id,
        "status": models_PRScan.status,
        "created_at": models_PRScan.created_at,
        "secret_count": literal_column("secret_count"),
        "vulnerability_count": literal_column("vulnerability_count")
    }

    sort_column = sort_columns.get(sort_by, models_PRScan.created_at)
    query = query.order_by(order(sort_column))

    # Pagination and results
    total_count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(total_count_query)
    result_query = paginate(query, total_count, page, limit)
    result = await db.execute(result_query['query'])

    pr_scans = result.fetchall()
    serialized_pr_scans = [
        PRScan(
            pr_id=row[0].pr_id,
            vc_id=row[0].vc_id,
            webhook_id=row[0].webhook_id,
            repo_id=row[0].repo_id,
            vc_type=row[0].vc_type,
            status=row[0].status,
            id=row[0].id,
            created_at=row[0].created_at,
            block_status=row[0].block_status,
            pr=row[0].pr,
            vc_name=row[0].vc.name if row[0].vc else None,
            repo_name=row[0].repository.name if row[0].repository else None,
            secret_count=row.secret_count,
            vulnerability_count=row.vulnerability_count,
            scan_type=row[0].scan_type
        ) for row in pr_scans
    ]

    return {"data": serialized_pr_scans, **result_query['meta']}





async def get_available_scan_filters() -> dict:
    return {
        "filters": [
            {"key": "vc_ids", "label": "VCs", "type": "api"},
            {"key": "repo_ids", "label": "Repositories", "type": "api"},
            {"key": "status", "label": "Status", "type": "boolean"},
            {"key": "pr_id", "label": "Pull Request", "type": "api"},
            {"key": "scan_type", "label": "Scan Type", "type": "text"},
            {"key": "sort_by", "label": "Sort By", "type": "text"},
            {"key": "order_by", "label": "Order By", "type": "text"}
        ]
    }

async def get_scan_filter_values(
    db: AsyncSession,
    filter_name: str,
    search: Optional[str] = None
) -> List:
    filter_map = {
        "vc_ids": models_PRScan.vc_id,
        "repo_ids": models_PRScan.repo_id,
        "status": models_PRScan.block_status,
        "pr_id": models_PRScan.pr_id,
        "scan_type": models_PRScan.scan_type,
    }
    
    if filter_name not in filter_map and filter_name not in {"sort_by", "order_by"}:
        raise HTTPException(status_code=400, detail="Invalid filter name")

    if filter_name in {"sort_by", "order_by"}:
        return (
            ["repo_name",
        "pr_id",
        "status",
        "created_at",
        "secret_count",
        "vulnerability_count"]
            if filter_name == "sort_by"
            else ["asc", "desc"]
        )

    column = filter_map[filter_name]
    query = select(distinct(column)).where(column.isnot(None))
    if search and isinstance(column.type, (String, TEXT)):
        query = query.where(column.ilike(f"%{search}%"))

    result = await db.execute(query)
    return result.scalars().all()




async def update_pr_scan(
        db: AsyncSession,
        pr_scan_id: int,
        pr_scan_update: PRScanUpdate
    ) -> models_PRScan:
    query = select(models_PRScan).filter_by(id=pr_scan_id)
    result = await db.execute(query)
    pr_scan = result.scalar_one_or_none()

    if not pr_scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PR Scan not found")

    for var, value in vars(pr_scan_update).items():
        if value is not None:
            setattr(pr_scan, var, value)

    await db.commit()
    await db.refresh(pr_scan)

    print(f'Updated PR status {pr_scan_id}')
    return pr_scan


async def get_pr_scan_by_id(
        db: AsyncSession,
        pr_scan_id: int) -> models_PRScan:
    query = select(models_PRScan).where(models_PRScan.id == pr_scan_id)
    result = await db.execute(query)
    pr_scan = result.scalar_one_or_none()

    if not pr_scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PR Scan not found")

    return pr_scan


async def get_pr_scans_by_status(
        db: AsyncSession,
        status: StatusEnum,
        page: int = 1,
        limit: int = 10) -> dict:
    query = select(models_PRScan).where(
        cast(models_PRScan.status, TEXT) == status.value)
    total_count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(total_count_query)
    result_query = paginate(query, total_count, page, limit)
    result = await db.execute(result_query['query'])

    pr_scans = result.scalars().all()
    serialized_pr_scans = [PRScan.from_orm(pr_scan) for pr_scan in pr_scans]

    return {"data": serialized_pr_scans, **result_query['meta']}




async def update_secret_count(
        db: AsyncSession,
        pr_scan_id: int,
        secret_count: int):
    query = select(models_PRScan).where(models_PRScan.id == pr_scan_id)
    result = await db.execute(query)
    pr_scan = result.scalar_one_or_none()

    if not pr_scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PR Scan not found")

    if secret_count == 0:
        return pr_scan

    pr_scan.secret_count = secret_count
    pr_scan.block_status = True

    await db.commit()
    await db.refresh(pr_scan)
    return pr_scan

