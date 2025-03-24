from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.modules.groups.groups_service import *
from app.modules.groups.schemas.group_schema import CreateGroupSchema, ReposRequest, GroupUpdateRequest, RepoFilterSchema
from app.modules.auth.auth_utils import role_required, get_current_user
from app.modules.user.models.user import UserRole
from typing import Optional, List
from sqlalchemy import asc, desc    
from fastapi import Query

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("/", dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def create_group_controller(
    group_data: CreateGroupSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Create a new group. Admin access required."""
    return await create_group(db, group_data, current_user)


@router.get("/filters",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_groups_filters():
    """Get available group filters."""
    return {
        "filters": [
            {"key": "repo_ids", "label": "Repositories", "type": "api"},
        ]
    }


@router.get("/filters/{filter_name}/values",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_groups_filters(filter_name: str):
    """Retrieve specific filter values for 'sort_by' and 'order_by'."""
    # if filter_name == 'sort_by':
    #     return {"values": ["repo_count", "created_at", "score"], "total": 3}
    # if filter_name == 'order_by':
    #     return {"values": ["asc", "desc"], "total": 2}
    return []


@router.get("/{group_id}",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_group(group_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch details for a specific group."""
    return await get_group_by_id(db, group_id)


@router.get(
    "/",
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))]
)
async def get_groups(
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = None,
    repo_ids: Optional[List[int]] = Query(None),  # Accept multiple `repo_ids` as a list
    sort_by: Optional[str] = "name",
    order_by: Optional[str] = "asc"
):
    """Retrieve paginated list of groups with optional search, filtering, and sorting."""
    return await get_all_groups(db, page, limit, search, repo_ids, sort_by, order_by)



@router.delete("/{group_id}",
               dependencies=[Depends(role_required([UserRole.admin,UserRole.user]))])
async def delete_group_controller(
        group_id: int,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    """Delete a group. Admin access required."""
    return await delete_group(db, group_id, current_user)


@router.get("/{group_id}/repos",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_repos_for_group_controller(
        group_id: int,
        db: AsyncSession = Depends(get_db)):
    """Retrieve repositories associated with a group."""
    try:
        return await get_repos_for_group(db, group_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{group_id}/add_repos",
            dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def add_repos_to_group_controller(
    group_id: int,
    repos_request: ReposRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Add multiple repositories to a group."""
    try:
        return await add_repos_to_group(db, group_id, repos_request.repo_ids, current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{group_id}/remove_repos",
            dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def remove_repos_from_group_controller(
    group_id: int,
    repos_request: ReposRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Remove multiple repositories from a group."""
    try:
        return await remove_repos_from_group(db, group_id, repos_request.repo_ids, current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{group_id}",
            dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def update_group_controller(
    group_id: int,
    body: GroupUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Update group details (name, description, or repositories). Admin access required."""
    try:
        result = await update_group(
            db,
            group_id,
            name=body.name,
            description=body.description,
            repos_ids=body.repos,
            current_user=current_user
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{group_id}/add_repos_by_filters",
            dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def add_repos_to_group_by_filters_controller(
    group_id: int,
    repo_filters: RepoFilterSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Add repositories to a group based on filter criteria (name, author, vc_id)."""
    return await add_repos_to_group_by_filters(db, group_id, repo_filters, current_user)


@router.put("/{group_id}/remove_repos_by_filters",
            dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def remove_repos_from_group_by_filters_controller(
    group_id: int,
    repo_filters: RepoFilterSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Remove repositories from a group based on filter criteria (name, author, vc_id)."""
    return await remove_repos_from_group_by_filters(db, group_id, repo_filters, current_user)
