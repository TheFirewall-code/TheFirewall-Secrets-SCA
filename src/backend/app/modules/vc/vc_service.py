from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc, func
from app.modules.vc.models.vc import VC
from app.modules.vc.schemas.vc_schema import VCCreate, VCResponse, VCUpdate
from sqlalchemy.future import select
from app.modules.user.models.user import User
from app.utils.pagination import paginate
from typing import Dict, List, Optional
from fastapi import BackgroundTasks, Query, HTTPException, status
from app.utils.string import mask_string
import httpx
from sqlalchemy.exc import IntegrityError
from app.utils.encoding_base_64 import encode_basic_token
from sqlalchemy.orm import joinedload, selectinload


async def validate_vc(vc: VCCreate):
    """
    Validate the VC token and URL by making an API call to the given VC service.
    """
    
    if vc.type.value == "bitbucket":
        token = encode_basic_token(vc.token)
        headers = {"Authorization": f"Basic {token}"}
    else: 
        headers = {"Authorization": f"Bearer {vc.token}"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(vc.url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to validate VC {vc.type}. Ensure the token and URL are correct."
                )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error connecting to {vc.type}: {e}"
        )

async def fetch_and_scan_repos(db, db_vc_id, current_user):
    # fetch all repos
    from app.modules.repository.repository_service import fetch_all_repos_for_vc, scan_all_repos_for_vc
    # Fetch all repositories
    await fetch_all_repos_for_vc(db, db_vc_id, current_user)
    # Run secret scans
    await scan_all_repos_for_vc(db, db_vc_id, current_user)

async def create_vc(
        db: AsyncSession,
        vc: VCCreate,
        current_user: User,
        background_tasks: BackgroundTasks) -> VCResponse:
    if not vc.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The `name` field is required."
        )

    # Validate the VC token and URL
    await validate_vc(vc)

    db_vc = VC(
        type=vc.type,
        token=vc.token,
        url=vc.url,
        name=vc.name,
        description=vc.description,
        added_by_user_id=current_user.id,
        created_by=current_user.id,
        updated_by=current_user.id
    )

    db.add(db_vc)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VC name already taken"
        )
    

    background_tasks.add_task(fetch_and_scan_repos, db, db_vc.id, current_user)

    # Run SCA scan
    from app.modules.vulnerability.vulnerability_service import scan_vulnerability_all_repos_for_vc
    background_tasks.add_task(
        scan_vulnerability_all_repos_for_vc,
        db,
        db_vc.id,
        current_user
    )
    
    await db.refresh(db_vc)
    return VCResponse.from_orm(db_vc)

async def get_vc(db: AsyncSession, vc_id: int, mask=False) -> VC:
    query = select(VC).filter(VC.id == vc_id)
    result = await db.execute(query)
    vc = result.scalars().one_or_none()
    if vc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VC not found"
        )
    if mask:
        vc.token = mask_string(vc.token)
    return vc

async def get_all_vcs(
    db: AsyncSession,
    vc_type: Optional[str] = None,
    sort_by: Optional[str] = None,
    order_by: Optional[str] = "asc",
    active: Optional[bool] = None,
    vc_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    mask=False
) -> Dict:
    query = select(VC).options(selectinload(VC.webhook_configs))


    if vc_type:
        query = query.filter(VC.type == vc_type)
    if vc_name:
        query = query.filter(VC.name.ilike(f"%{vc_name}%"))

    if sort_by in {"type", "created_at"}:
        order_func = asc if order_by == "asc" else desc
        query = query.order_by(order_func(getattr(VC, sort_by)))

    if active:
        query = query.filter(VC.active == active)

    # Get the total count of records for pagination metadata
    total_count_query = select(func.count()).select_from(query.subquery())
    total_count_result = await db.execute(total_count_query)
    total_count = total_count_result.scalar()

    # Paginate the query results
    paginated_query = paginate(query, total_count, page, limit)
    result = await db.execute(paginated_query['query'])
    vcs = result.scalars().all()

    # Convert SQLAlchemy objects to Pydantic models
    vcs = [VCResponse.from_orm(vc) for vc in vcs]
    if mask:
        for vc in vcs:
            vc.token = mask_string(vc.token)

    return {
        "data": vcs,
        **paginated_query['meta']
    }

async def get_distinct_vc_types(db: AsyncSession) -> List[str]:
    query = select(VC.type).distinct()
    result = await db.execute(query)
    vc_types = result.scalars().all()
    return vc_types

async def update_vc(
        db: AsyncSession,
        vc_id: int,
        vc: VCUpdate,
        current_user: User,
        background_tasks: BackgroundTasks) -> Optional[VC]:

    query = select(VC).filter(VC.id == vc_id)
    result = await db.execute(query)
    db_vc = result.scalars().first()

    if db_vc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VC not found"
        )

    if vc.token:
        db_vc.token = vc.token
    if vc.url:
        db_vc.url = vc.url
    if vc.name:
        db_vc.name = vc.name
    if vc.description:
        db_vc.description = vc.description
    if vc.active is not None:
        db_vc.active = vc.active

    db_vc.updated_by = current_user.id

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update VC due to an integrity error."
        )

    await db.refresh(db_vc)

    # Get and scan all repos
    if db_vc.active:
        from app.modules.repository.repository_service import fetch_all_repos_for_vc, scan_all_repos_for_vc
        background_tasks.add_task(
            fetch_all_repos_for_vc,
            db,
            db_vc.id,
            current_user)
        background_tasks.add_task(
            scan_all_repos_for_vc,
            db,
            db_vc.id,
            current_user)

        # Run SCA scan
        from app.modules.vulnerability.vulnerability_service import scan_vulnerability_all_repos_for_vc
        background_tasks.add_task(
            scan_vulnerability_all_repos_for_vc,
            db,
            db_vc.id,
            current_user
        )

    return db_vc

async def delete_vc(
        db: AsyncSession,
        vc_id: int,
        current_user: User) -> VCResponse:
    

    from app.modules.licenses.licesses_service import validate_license
    query = select(VC).filter(VC.id == vc_id)
    result = await db.execute(query)
    db_vc = result.scalars().first()

    if db_vc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VC not found"
        )

    db_vc.active = False
    db_vc.updated_by = current_user.id

    await db.commit()
    await db.refresh(db_vc)
    return db_vc

async def disable_all_vc(db: AsyncSession) -> bool:
    """
    Disable (soft delete) all VC records by setting `active = False`.
    """

    # Fetch all active VCs
    query = select(VC).filter(VC.active == True)
    result = await db.execute(query)
    vcs = result.scalars().all()

    if not vcs:
        return True

    # Disable all VCs
    for vc in vcs:
        vc.active = False
    await db.commit()

    for vc in vcs:
        await db.refresh(vc)

    return True
