from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.modules.live_commits.live_commits_service import (
    get_live_commits,
    get_live_commit_filters,
    get_live_commit_filter_values,
)
from app.modules.live_commits.live_commits_scans_service import (
    get_live_commits_scan,
    get_live_commit_scan_filters,
    get_live_commit_scan_filter_values,
    get_scan_with_commits,
)
from app.modules.auth.auth_utils import role_required, get_current_user
from app.modules.user.models.user import UserRole
from typing import List
from app.modules.live_commits.models.live_commits_scan import LiveCommitScanType

router = APIRouter(prefix="/live_commits", tags=["Live Commits"])

# Route to get live commits with pagination and vc_id, repo_id as arrays


@router.get("/",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_live_commits_endpoint(
    vc_ids: List[int] = Query(None, description="List of VC IDs"),
    repo_ids: List[int] = Query(None, description="List of Repo IDs"),
    branch_name: str = Query(None),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Number of items per page"),
    sort_by: str = Query('created_at'),
    order_by: str = Query('desc'),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    live_commits = await get_live_commits(
        db=db,
        vc_ids=vc_ids,
        repo_ids=repo_ids,
        branch_name=branch_name,
        page=page,
        limit=limit,
        sort_by=sort_by,
        order_by=order_by,
    )

    if not live_commits:
        return []

    return live_commits


@router.get("/scan/filters",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_live_commit_scan_filters_endpoint(
        db: AsyncSession = Depends(get_db)):
    return await get_live_commit_scan_filters(db)


@router.get("/scan/{filter_name}/filters",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_live_commit_scan_filter_values_endpoint(
        filter_name: str, db: AsyncSession = Depends(get_db)):
    return await get_live_commit_scan_filter_values(db, filter_name)


@router.get("/filters",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_live_commit_filters_endpoint(db: AsyncSession = Depends(get_db)):
    return await get_live_commit_filters(db)


@router.get("/{filter_name}/filters",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_live_commit_filter_values_endpoint(
        filter_name: str, db: AsyncSession = Depends(get_db)):
    return await get_live_commit_filter_values(db, filter_name)


# Route to get live commits for a specific scan ID
@router.get("/scan/{scan_id}/commits/",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_commits_for_scan_endpoint(
        scan_id: int,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    scan_with_commits = await get_scan_with_commits(db, scan_id)

    if not scan_with_commits:
        return []

    return scan_with_commits

# Route to get live commit scans with pagination, vc_id, repo_id, and search functionality
@router.get(
    "/scan/",
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))]
)
async def get_live_commits_scan_endpoint(
    vc_ids: List[int] = Query(None, description="List of VC IDs"),
    repo_ids: List[int] = Query(None, description="List of Repo IDs"),
    commit_ids: List[str] = Query(None, description="List of Commit IDs"),  # New parameter for commit IDs
    author: str = Query(None, description="Filter by author name"),  # New parameter for author name
    commit_msg: str = Query(None, description="Filter by commit message"),  # New parameter for commit message
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Number of items per page"),
    scan_type: LiveCommitScanType = Query(LiveCommitScanType.SECRET, description="Filter by scan type: SECRET or VULNERABILITY"),
    search: str = Query(None, description="Search across all parameters"),
    sort_by: str = Query(None, description="Sort by 'repo_count', 'secret_count', or 'vulnerability_count'"),
    order_by: str = Query('asc', description="Order by 'asc' or 'desc'"),  # Default to ascending order
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Pass the new parameters to the service function
    live_commit_scans = await get_live_commits_scan(
        db=db,
        vc_ids=vc_ids,
        repo_ids=repo_ids,
        commit_ids=commit_ids,  # Commit IDs parameter passed
        author=author,  # Author name parameter passed
        commit_msg=commit_msg,  # Commit message parameter passed
        page=page,
        limit=limit,
        live_commit_scan_type=scan_type,
        search=search,
        sort_by=sort_by,
        order_by=order_by
    )

    if not live_commit_scans["data"]:
        return []

    return live_commit_scans



