# app/models/otp.py
import uuid
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, DateTime, func, Boolean

from app.utils.postgresql_db_util import db_util

base = db_util.base

class OTPModel(base):
    __tablename__ = 'otps'
    __table_args__ = ({'schema': 'public'})

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    purpose = Column(String, nullable=False)  # 'registration', 'login', 'reset_password'
    expires_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(minutes=10))
    is_used = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        """Convert model to dictionary for serialization"""
        return {
            "id": str(self.id),
            "phone_number": self.phone_number,
            "code": self.code,
            "purpose": self.purpose,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_used": self.is_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"OTPModel(id={self.id}, phone_number={self.phone_number}, code={self.code}, purpose={self.purpose})"
