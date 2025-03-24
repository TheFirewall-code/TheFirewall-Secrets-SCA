from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from app.modules.repository.repository_service import (
    fetch_all_repos_for_vc,
    get_repos,
    get_available_filters,
    get_filter_values,
    scan_repo_by_id,
    scan_all_repos_for_vc,
    get_repo_by_id,
    update_sca_branches,
    generate_sbom_for_repo
)
from app.modules.repository.models.repository import Repo
from app.modules.repository.schemas.repository_schema import (
    FetchReposRequest,
    RepoId,
    SortByEnum,
    FilterValueCount,
    FilterOption
)
import json
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from app.core.db import get_db
from app.modules.auth.auth_utils import role_required, get_current_user
# from app.modules.vulnerability.vulnerability_service import scan_vulnerability_repo_by_id
from app.modules.user.models.user import UserRole
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/repo", tags=["Repositories"])

# Fetch all the repos


@router.post("/fetch/all",
             dependencies=[Depends(role_required([UserRole.admin,
                                                  UserRole.user,
                                                  UserRole.readonly]))])
async def fetch_all_repos_for_vc_endpoint(
        request: FetchReposRequest,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    try:
        await fetch_all_repos_for_vc(db, request.vc_id, current_user)
        return {"message": "Repositories fetched and stored successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e))


@router.get("/",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_repos_controller(
    search: Optional[str] = None,
    vc_ids: List[int] = Query(None, description="List of VC IDs"),
    repo_ids: List[int] = Query(None, description="List of repository IDs"),
    authors: List[str] = Query(None, description="Authors"),
    sort_by: SortByEnum = SortByEnum.CREATED_AT,
    order_by: Optional[str] = "desc",
    page: int = 1,
    limit: int = 10,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        repos = await get_repos(
            db=db,
            sort_by=sort_by.value if sort_by else None,
            order_by=order_by,
            page=page,
            vc_ids=vc_ids,
            repo_ids=repo_ids,
            created_after=created_after,
            created_before=created_before,
            search=search,
            limit=limit,
            authors=authors
        )
        return repos
    except ValidationError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ve.errors())
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error")


@router.get("/filters",
            response_model=List[FilterOption],
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_filters():
    return await get_available_filters()


@router.get("/filters/{filter_key}/values",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_filter_values_endpoint(
    filter_key: str,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await get_filter_values(
            db=db,
            filter_key=filter_key,
            search=search,
            page=page,
            limit=limit
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error")

# Scan for secrets for a particular repo


@router.post("/scan",
             dependencies=[Depends(role_required([UserRole.admin,
                                                  UserRole.user,
                                                  UserRole.readonly]))])
async def scan_repo_by_id_endpoint(
        request: RepoId,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    try:
        return await scan_repo_by_id(db, request.repository_id, current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e))


@router.post("/scan/all",
             dependencies=[Depends(role_required([UserRole.admin,
                                                  UserRole.user,
                                                  UserRole.readonly]))])
async def scan_all_repos_for_vc_endpoint(
        request: FetchReposRequest,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)):
    try:
        return await scan_all_repos_for_vc(db, request.vc_id, current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e))


@router.get("/{repo_id}")
async def get_repo(repo_id: int, db: AsyncSession = Depends(get_db)):
    try:
        repo = await get_repo_by_id(db, repo_id)
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repo_id} not found")
        return repo
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}")

@router.put("/{repo_id}/sca-branches",
            dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def update_sca_branches_endpoint(
    repo_id: int,
    sca_branches: List[str],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        updated_repo = await update_sca_branches(db, repo_id, sca_branches, current_user)
        if not updated_repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repo_id} not found"
            )
        return {"message": "SCA branches updated successfully", "sca_branches": updated_repo.sca_branches}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{repo_id}/sbom", dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def generate_sbom_for_repo_endpoint(
    repo_id: int,
    branch: str = Query(None, description="Branch name to generate SBOM for"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        # Call the service to generate SBOM for the repository
        sbom_data = await generate_sbom_for_repo(db, repo_id, branch)

        # If SBOM data is returned, send it in the response
        return {
            "repo_name": sbom_data["repo_name"],
            "repo_url": sbom_data["repo_url"],
            "sbom": sbom_data["sbom"]
        }
    except HTTPException as e:
        # Re-raise the HTTPException if it occurs in the service
        raise e
    except Exception as e:
        # Handle other exceptions
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@router.get("/repo/{repo_id}/sbom/download", dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def download_sbom_for_repo(
    repo_id: int,
    branch: str = Query(None, description="Branch name to generate SBOM for"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        # Generate SBOM using the existing service function
        sbom_data = await generate_sbom_for_repo(db, repo_id, branch)

        # Convert the SBOM data to JSON and stream it
        sbom_json = json.dumps(sbom_data["sbom"])
        sbom_stream = BytesIO(sbom_json.encode("utf-8"))

        # Prepare a StreamingResponse with the appropriate headers
        response = StreamingResponse(
            sbom_stream,
            media_type="application/json"
        )
        response.headers["Content-Disposition"] = f"attachment; filename={sbom_data['repo_name']}_sbom.json"

        return response

    except HTTPException as e:
        # Re-raise HTTPException from the service layer
        raise e
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )