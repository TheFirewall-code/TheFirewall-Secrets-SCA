from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.licenses.licenses_schema import LicenseCreate, LicenseVerify
from app.modules.licenses.licesses_service import create_license, validate_license, verify_license
from app.core.db import get_db
from app.modules.auth.auth_utils import role_required
from app.modules.user.models.user import UserRole

router = APIRouter(prefix="/license", tags=['License'])

@router.post("/generate", dependencies=[])
async def generate_license_route(license_req: LicenseCreate, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to create (request) a new license for the given email.
    """
    result = create_license(license_req.email)
    return result

@router.post("/verify", dependencies=[])
async def verify_license_route(license_req: LicenseVerify, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to create (request) a new license for the given email.
    """
    result = await verify_license(db, license_req.otp, license_req.license_id)
    return {
        "message": "License generated successfully",
        "data": result
    }

@router.get("/validate", dependencies=[])
async def validate_license_route(db: AsyncSession = Depends(get_db)):
    """
    Endpoint to validate the existing license token locally or via the server.
    """
    is_valid = await validate_license(db)
    return {
        "valid": is_valid
    }
