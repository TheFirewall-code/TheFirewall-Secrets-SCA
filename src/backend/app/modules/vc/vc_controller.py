from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict
from app.modules.vc.schemas.vc_schema import VCCreate, VCResponse, VCUpdate
from app.core.db import get_db
from app.modules.vc.vc_service import *
from app.modules.auth.auth_utils import role_required, get_current_user
from app.modules.user.models.user import UserRole


router = APIRouter(prefix="/vc", tags=["Version Control"])

@router.post("/",
             response_model=VCResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required([UserRole.admin]))])
async def create_vc_controller(
        vc: VCCreate,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    return await create_vc(db=db, vc=vc, current_user=current_user, background_tasks=background_tasks)


@router.get("/{vc_id}",
            response_model=VCResponse,
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_vc_controller(
        vc_id: int,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    return await get_vc(db=db, vc_id=vc_id, mask=True)


@router.get("/",
            response_model=Dict,
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_all_vcs_controller(
    vc_type: Optional[str] = None,
    sort_by: Optional[str] = None,
    order_by: Optional[str] = "asc",
    active: Optional[bool] = None,
    vc_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await get_all_vcs(
        db=db,
        vc_type=vc_type,
        sort_by=sort_by,
        order_by=order_by,
        active=active,
        vc_name=vc_name,
        page=page,
        limit=limit,
        mask=True
    )


@router.get("/distinct/vc_types",
            response_model=List[str],
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_distinct_vc_types_controller(
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    return await get_distinct_vc_types(db=db)


@router.put("/{vc_id}", response_model=VCResponse,
            dependencies=[Depends(role_required([UserRole.admin]))])
async def update_vc_controller(
        vc_id: int,
        vc: VCUpdate,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    return await update_vc(db=db, vc_id=vc_id, vc=vc, current_user=current_user, background_tasks=background_tasks)


@router.delete("/{vc_id}",
               response_model=VCResponse,
               status_code=status.HTTP_200_OK,
               dependencies=[Depends(role_required([UserRole.admin]))])
async def delete_vc_controller(
        vc_id: int,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    return await delete_vc(db=db, vc_id=vc_id, current_user=current_user)
