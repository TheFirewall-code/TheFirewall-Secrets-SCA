from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.modules.auth.auth_utils import role_required
from app.modules.user.models.user import UserRole
from typing import List, Dict
from app.modules.scoring.repository_property_service import RepositoryPropertyService
from app.modules.scoring.schema.schema import (
    PropertyType,
    PropertyResponse,
    PropertyCreate,
    PropertyUpdate,
    AttachPropertyRequest
)

router = APIRouter(prefix="/repo/property", tags=["Repository Properties"])


@router.get("/{property_type}",
            response_model=List[PropertyResponse],
            dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def get_properties(
    property_type: PropertyType,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all properties of a given type.
    """
    try:
        return await RepositoryPropertyService.get_properties(db, property_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{property_type}",
             response_model=PropertyResponse,
             dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def create_property(
    property_type: PropertyType,
    data: PropertyCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new property.
    """
    try:
        return await RepositoryPropertyService.create_property(db, property_type, data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{property_type}/{property_id}",
            response_model=PropertyResponse,
            dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def update_property(
    property_type: PropertyType,
    property_id: int,
    data: PropertyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing property.
    """
    try:
        return await RepositoryPropertyService.update_property(db, property_type, property_id, data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{property_type}/{property_id}",
               dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def delete_property(
    property_type: PropertyType,
    property_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a property.
    """
    try:
        await RepositoryPropertyService.delete_property(db, property_type, property_id)
        return {"message": f"{property_type.value} deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/repository/{repo_id}/properties",
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_repo_properties(
    repo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all associated properties of a given repository by repo_id.
    """
    try:
        properties = await RepositoryPropertyService.get_repo_properties(db, repo_id)
        return properties
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Repository not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/repository/{repo_id}/properties",
             dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def attach_property_to_repo(
    repo_id: int,
    request: AttachPropertyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Attach a property to a repository.
    """
    try:
        await RepositoryPropertyService.attach_property_to_repo(db, repo_id, request)
        return {
            "message": f"{request.property_type.value} attached successfully to repository."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/repository/{repo_id}/properties",
               dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def remove_property_from_repo(
    repo_id: int,
    property_type: PropertyType,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a property from a repository.
    """
    try:
        await RepositoryPropertyService.remove_property_from_repo(db, repo_id, property_type)
        return {"message": f"{property_type.value} removed from repository."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
