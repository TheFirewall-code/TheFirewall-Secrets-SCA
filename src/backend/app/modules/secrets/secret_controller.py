from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.modules.secrets.schema.secret_schema import (
    SecretsCreate,
    SecretsResponse,
    SecretsUpdate,
    FilterValueResponse,
    GetSecretsRequest,
    SecretsResponsePagniation
)
from app.modules.secrets.secret_service import (
    add_secret,
    get_secret_by_id,
    get_available_filters,
    get_filter_values,
    update_secret,
    delete_secret,
    get_secrets_by_param_service,
    get_distinct_secrets_with_repos,
    get_repos_for_secret
)
from app.core.logger import logger
from app.modules.auth.auth_utils import role_required, get_current_user
from app.modules.user.models.user import UserRole
from app.utils.pagination import Pagination

router = APIRouter(prefix="/secrets", tags=["Secrets"])


@router.post("/",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def list_secrets(
        params: GetSecretsRequest = Body(..., description="Secrets fetch parameters"),
        db: AsyncSession = Depends(get_db)
):

    # Fetch secrets using service with dynamic filters
    secrets = await get_secrets_by_param_service(
        db=db,
        query=params,
        search=params.search,
        repo_ids=params.repo_ids,
        vc_ids=params.vc_ids,
        pr_ids=params.pr_ids,
        page=params.page,
        limit=params.limit
    )

    # logger.debug(f"Returning {len(secrets['secrets'])} secrets.")
    return secrets


@router.post(
    "/unique",
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))],
)
async def list_secrets(
    params: GetSecretsRequest = Body(..., description="Secrets fetch parameters"),
    db: AsyncSession = Depends(get_db)
):
    # Call the service function passing all parameters from the request model.
    secrets = await get_distinct_secrets_with_repos(
        db=db,
        query=params,
        search=params.search,
        repo_ids=params.repo_ids,
        vc_ids=params.vc_ids,
        pr_ids=params.pr_ids,
        page=params.page,
        limit=params.limit
    )
    return secrets


@router.get("/:secret_name/repos",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def list_secrets(
    secret_name: str = Query(None, description="Secret name"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):

    # Fetch secrets using service with dynamic filters
    return await get_repos_for_secret(
        db,
        secret_name=secret_name,
        page=page,
        limit=limit
    )


@router.get("/filters",
            response_model=dict,
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_filters(db: AsyncSession = Depends(get_db)):
    logger.info("Request received to fetch available filters for secrets")
    filters = await get_available_filters(db)
    return filters


@router.get("/filters/{filter_name}/values",
            response_model=FilterValueResponse,
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_filter_values_endpoint(
    filter_name: str,
    search: Optional[str] = Query(None, description="Search for specific filter values"),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    logger.info(
        f"Request received to fetch distinct values for filter: {filter_name}, search={search}, page: {page}, page_size: {page_size}")

    # Fetch filter values using the service
    values, total = await get_filter_values(db, filter_name, search, page, page_size)

    return FilterValueResponse(values=values, total=total)


@router.get("/{secret_id}",
            response_model=SecretsResponse,
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_secret(secret_id: int, db: AsyncSession = Depends(get_db)):
    logger.info(f"Request received to fetch secret with id: {secret_id}")
    secret = await get_secret_by_id(db, secret_id)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Secret not found")
    return secret
