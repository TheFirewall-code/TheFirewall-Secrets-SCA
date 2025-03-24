from pydantic import BaseModel
from typing import Optional
from enum import Enum


class BusinessCriticalityModel(BaseModel):
    id: Optional[int]
    name: str
    value: float


class EnvironmentModel(BaseModel):
    id: Optional[int]
    name: str
    value: float


class DataSensitivityModel(BaseModel):
    id: Optional[int]
    name: str
    value: float


class RegulatoryRequirementModel(BaseModel):
    id: Optional[int]
    name: str
    value: float


class PropertyType(str, Enum):
    BUSINESS_CRITICALITY = "business_criticalities"
    ENVIRONMENT = "environments"
    DATA_SENSITIVITY = "data_sensitivities"
    REGULATORY_REQUIREMENT = "regulatory_requirements"


class PropertyBase(BaseModel):
    name: str
    value: float


class PropertyResponse(PropertyBase):
    id: int

    class Config:
        from_attributes = True


class AttachPropertyRequest(BaseModel):
    property_id: int
    repo_id: int
    property_type: PropertyType


class PropertyType(str, Enum):
    BUSINESS_CRITICALITY = "business_criticalities"
    ENVIRONMENT = "environments"
    DATA_SENSITIVITY = "data_sensitivities"
    REGULATORY_REQUIREMENT = "regulatory_requirements"


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(PropertyBase):
    value: float


class PropertyResponse(PropertyBase):
    id: int

    class Config:
        from_attributes = True


class AttachPropertyRequest(BaseModel):
    property_id: int
    property_type: PropertyType
