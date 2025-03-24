from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LicenseCreate(BaseModel):
    email: str

class LicenseResponse(BaseModel):
    email: str

class LicenseVerify(BaseModel):
    otp: str
    license_id: str