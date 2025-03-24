from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.core.db import get_db
from app.modules.auth.auth_utils import role_required
from app.modules.user.models.user import UserRole
from app.modules.pr.schemas.pr_schema import PRInDB
from app.modules.pr.schemas.pr_scan_schema import PRScan, PRScanType
from app.modules.pr.models.pr_scan import StatusEnum
from app.modules.pr.pr_service import (
    get_pr,
    get_pr_by_id,
    get_available_filters,
    get_filter_values
)
from app.modules.pr.pr_scan_service import (
    get_pr_scan,
    get_pr_scan_by_id,
    get_pr_scans_by_status,
    get_available_scan_filters,
    get_scan_filter_values
)

router = APIRouter(prefix="/pr", tags=["Pull Request"])

@router.get(
    "/",
    response_model=dict,
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))]
)
async def list_pr(
    pr_id: Optional[int] = None,
    repo_ids: Optional[List[int]] = Query(None, description="List of Repo IDs"),
    vc_ids: Optional[List[int]] = Query(None, description="List of VC IDs"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    pr_name: Optional[str] = None,
    search: Optional[str] = None
):
    return await get_pr(
        db=db,
        pr_id=pr_id,
        vc_ids=vc_ids,
        repo_ids=repo_ids,
        pr_name=pr_name,
        search=search,
        page=page,
        limit=limit
    )

@router.get("/scans/filter",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_scan_filters():
    return await get_available_scan_filters()


@router.get("/scans/{filter_name}/filter",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_scan_filter_values_controller(
    filter_name: str,
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(
        None,
        description="Search for specific filter values"),
):
    return await get_scan_filter_values(db, filter_name, search)


@router.get("/filter",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_filters():
    return await get_available_filters()


@router.get("/{filter_name}/filter",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_filter_values_controller(
    filter_name: str,
    db: AsyncSession = Depends(get_db)
):
    return await get_filter_values(db, filter_name)



@router.get(
    "/scans/",
    response_model=dict,
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))]
)
async def list_pr_scans(
    pr_scan_id: Optional[int] = None,
    pr_id: Optional[int] = None,
    repo_ids: Optional[List[int]] = Query(None, description="List of Repo IDs"),
    webhook_id: Optional[int] = None,
    status: Optional[bool] = Query(None, description="if PR is blocked or approved"),
    vc_ids: Optional[List[int]] = Query(None, description="List of VC IDs"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Number of items per page"),
    sort_by: Optional[str] = Query('created_at', description="Field to sort by"),
    order_by: Optional[str] = Query('desc'),
    scan_type: Optional[PRScanType] = Query(PRScanType.SECRET, description="Type of scan"),
    search: Optional[str] = Query(None, description="Search across PR scan parameters"),  # New search parameter
    db: AsyncSession = Depends(get_db)
):
    return await get_pr_scan(
        db=db,
        pr_scan_id=pr_scan_id,
        pr_id=pr_id,
        repo_ids=repo_ids,
        webhook_id=webhook_id,
        vc_ids=vc_ids,
        status=status,
        page=page,
        limit=limit,
        sort_by=sort_by,
        order_by=order_by,
        scan_type=scan_type,
        search=search  # Pass the new search parameter to get_pr_scan
    )


@router.get("/{pr_id}",
            response_model=PRInDB,
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_pr_by_id_route(
    pr_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await get_pr_by_id(db, pr_id)


@router.get("/scan/{pr_scan_id}",
            response_model=PRScan,
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_pr_scan_by_id_route(
    pr_scan_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await get_pr_scan_by_id(db, pr_scan_id)


@router.get("/scans/status/",
            response_model=dict,
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_pr_scans_by_status(
    status: StatusEnum,
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    return await get_pr_scans_by_status(db, status, page, limit)
