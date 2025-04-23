# app/schemas/user_schema.py
import re
from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


# Phone number validation regex for Nigerian numbers
NIGERIAN_PHONE_REGEX = r"^(\+?234|0)[789]\d{9}$"

class PhoneNumber(BaseModel):
    phone_number: str

    @classmethod
    @field_validator('phone_number')
    def validate_nigerian_phone(cls, v):
        if not re.match(NIGERIAN_PHONE_REGEX, v):
            raise ValueError('Invalid Nigerian phone number format')
        return v

class UserBase(BaseModel):
    phone_number: str
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    business_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool = True

class UserCreate(PhoneNumber):
    otp: str

class UserCompleteProfile(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    business_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    profile_image_url: Optional[str] = None

class UserInDB(UserBase):
    id: UUID
    is_phone_verified: bool
    is_email_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class User(UserInDB):
    pass

class UserPublic(BaseModel):
    id: UUID
    business_name: Optional[str] = None
    profile_image_url: Optional[str] = None

    class Config:
        orm_mode = True