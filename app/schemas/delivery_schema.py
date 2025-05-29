# app/schemas/delivery_schema.py
import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# Enhanced Location schema
class Location(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    timestamp: Optional[int] = Field(None, description="Timestamp of location capture")
    accuracy: Optional[float] = Field(None, description="Location accuracy in meters")
    speed: Optional[float] = Field(None, description="Speed in meters per second")
    address: Optional[str] = Field(None, description="Human-readable address")
    source: Optional[str] = Field(None, description="Source of location capture")

    @field_validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90 degrees')
        return v

    @field_validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180 degrees')
        return v


# Enhanced Customer information schema
class CustomerInfo(BaseModel):
    name: str = Field(..., min_length=1)
    phone_number: str = Field(..., min_length=10)
    address: str = Field(..., min_length=5)
    location: Optional[Location] = Field(None, description="Precise GPS coordinates of delivery location")

    @classmethod
    @field_validator('phone_number')
    def validate_phone(cls, v):
        pattern = r'^(\+?234|0)[789]\d{9}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid Nigerian phone number')
        return v


# Rider information schema (unchanged)
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


# Package information schema (unchanged)
class PackageInfo(BaseModel):
    description: str = Field(..., min_length=1)
    size: Optional[str] = Field(None, pattern='^(small|medium|large)$')
    special_instructions: Optional[str] = None


# Enhanced Create delivery schema
class CreateDelivery(BaseModel):
    customer: CustomerInfo
    rider: RiderInfo
    package: PackageInfo


# Enhanced Delivery response schema
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


# Delivery filter schema (unchanged)
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