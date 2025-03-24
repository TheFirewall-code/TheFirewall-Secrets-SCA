from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.modules.whitelist.schema.whitelist_schema import (
    WhitelistCreate, WhitelistUpdate, WhitelistResponse, WhitelistUpdateResponse, WhiteListType
)
from app.modules.whitelist.whitelist_service import (
    add_whitelist, get_whitelist, update_whitelist, get_filter_values, get_filters
)
from app.core.db import get_db
from app.modules.user.models.user import UserRole, User
from app.modules.auth.auth_utils import role_required, get_current_user

router = APIRouter(
    prefix="/whitelist",
    tags=["Whitelist secrets"]
)

# Create a new whitelist entry
@router.post("/", dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def create_whitelist(
    whitelist_data: WhitelistCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    print("Creating whitelist entry...")
    return await add_whitelist(db, whitelist_data, current_user)


# Fetch whitelist entries with filtering and pagination
@router.get(
    "/",
    response_model=dict,
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))]
)
async def fetch_whitelist(
    vc_ids: Optional[List[int]] = Query(None),
    repo_ids: Optional[List[int]] = Query(None),
    name: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    type: WhiteListType = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    sort_by: Optional[str] = Query("id", description="Sort by field, e.g., vcs, repos"),
    order_by: Optional[str] = Query("asc", description="Order direction: asc or desc"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    repo_whitelist: Optional[bool] = Query(default=False, description="Send only repo whitelist")
):
    return await get_whitelist(
        db, 
        vc_ids=vc_ids, 
        repo_ids=repo_ids, 
        name=name, 
        search=search,
        page=page, 
        limit=limit, 
        sort_by=sort_by, 
        order_by=order_by,
        type=type,
        repo_whitelist=repo_whitelist
    )

# Fetch available filter options for whitelist
@router.get("/filter", response_model=dict, dependencies=[Depends(get_current_user)])
async def fetch_filters(db: Session = Depends(get_db)):
    return await get_filters()


@router.get("/{value}/filter", response_model=dict, dependencies=[Depends(get_current_user)])
async def fetch_filter_values(
    value: str,
    page: int = Query(1, ge=1, description="Page number (starting from 1)"),
    page_size: int = Query(10, ge=1, description="Number of items per page"),
    db: Session = Depends(get_db),
):
    # Fetch filter values with pagination
    filter_values = await get_filter_values(db, value, page=page, page_size=page_size)
    if not filter_values:
        raise HTTPException(status_code=404, detail=f"No filter values found for '{value}'")
    return filter_values


# Update an existing whitelist entry
@router.put("/{whitelist_id}", response_model=WhitelistUpdateResponse, dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def modify_whitelist(
    whitelist_id: int,
    whitelist_data: WhitelistUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await update_whitelist(db, whitelist_id, whitelist_data, current_user)
