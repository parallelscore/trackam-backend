# app/schemas/rider_schema.py
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class OtpVerification(BaseModel):
    """
    Schema for OTP verification by riders.
    """
    tracking_id: str = Field(..., description="Tracking ID of the delivery")
    otp: str = Field(..., description="OTP code to verify")

    @classmethod
    @field_validator('otp')
    def validate_otp(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError('OTP must be a 6-digit number')
        return v


class LocationUpdate(BaseModel):
    """
    Schema for rider location updates.
    """
    tracking_id: str = Field(..., description="Tracking ID of the delivery")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    accuracy: Optional[float] = Field(None, description="Location accuracy in meters")
    speed: Optional[float] = Field(None, description="Speed in meters per second")
    battery_level: Optional[int] = Field(None, description="Battery level percentage")
    is_moving: Optional[bool] = Field(True, description="Whether the rider is moving")
