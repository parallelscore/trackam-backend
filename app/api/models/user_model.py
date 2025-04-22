# app/api/models/user_model.py
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, Boolean, DateTime, func

from app.utils.postgresql_db_util import db_util

base = db_util.base


class UserModel(base):

    __tablename__ = 'users'
    __table_args__ = ({'schema': 'public'})

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    business_name = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)

    is_phone_verified = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": str(self.id),
            "phone_number": self.phone_number,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "business_name": self.business_name,
            "profile_image_url": self.profile_image_url,
            "is_phone_verified": self.is_phone_verified,
            "is_email_verified": self.is_email_verified,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at)
        }

    def __repr__(self):
        return f"UserModel(id={self.id}, phone_number={self.phone_number}, email={self.email})"
