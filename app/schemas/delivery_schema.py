# app/schemas/delivery_schema.py
import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# Location schema
class Location(BaseModel):
    latitude: float
    longitude: float
    timestamp: int
    accuracy: Optional[float] = None
    speed: Optional[float] = None

# Customer information schema
class CustomerInfo(BaseModel):
    name: str = Field(..., min_length=1)
    phone_number: str = Field(..., min_length=10)
    address: str = Field(..., min_length=5)

    @classmethod
    @field_validator('phone_number')
    def validate_phone(cls, v):
        pattern = r'^(\+?234|0)[789]\d{9}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid Nigerian phone number')
        return v

# Rider information schema
class RiderInfo(BaseModel):
    name: str = Field(..., min_length=1)
    phone_number: str = Field(..., min_length=10)

    @classmethod
    @field_validator('phone_number')
    def validate_phone(cls, v):
        pattern = r'^(\+?234|0)[789]\d{9}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid Nigerian phone number')
        return v

# Package information schema
class PackageInfo(BaseModel):
    description: str = Field(..., min_length=1)
    size: Optional[str] = Field(None, pattern='^(small|medium|large)$')
    special_instructions: Optional[str] = None

# Create delivery schema
class CreateDelivery(BaseModel):
    customer: CustomerInfo
    rider: RiderInfo
    package: PackageInfo

# Delivery response schema
class DeliveryResponse(BaseModel):
    id: str
    tracking_id: str
    status: str
    customer: Dict[str, Any]
    rider: Optional[Dict[str, Any]] = None
    package: Dict[str, Any]
    tracking: Dict[str, Any]
    estimated_delivery_time: Optional[str] = None
    created_at: str
    updated_at: str

# Delivery filter schema
class DeliveryFilter(BaseModel):
    status: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    limit: int = 10

class DeliveryStats(BaseModel):
    total_deliveries: int
    in_progress: int
    completed: int
    cancelled: int
    completion_rate: int  # percentage
    avg_delivery_time: int  # minutes
    cancel_rate: int  # percentage
