# app/api/models/delivery_model.py
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Float, func

from app.api.models.user_model import UserModel
from app.utils.postgresql_db_util import db_util

base = db_util.base


class DeliveryModel(base):

    __tablename__ = "deliveries"
    __table_args__ = ({'schema': 'public'})

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracking_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(Enum('created', 'assigned', 'accepted', 'in_progress', 'completed', 'cancelled', name='delivery_status'), default='created')

    # Vendor information
    vendor_id = Column(UUID(as_uuid=True), ForeignKey(UserModel.id), nullable=False)

    # Customer information
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    customer_address = Column(String, nullable=False)
    customer_location = Column(JSONB, nullable=True)  # For storing lat/lng

    # Rider information
    rider_id = Column(UUID(as_uuid=True), ForeignKey(UserModel.id), nullable=True)
    rider_name = Column(String, nullable=True)
    rider_phone = Column(String, nullable=True)
    rider_current_location = Column(JSONB, nullable=True)  # For storing current lat/lng

    # Package information
    package_description = Column(String, nullable=False)
    package_size = Column(Enum('small', 'medium', 'large', name='package_size'), nullable=True)
    package_weight = Column(Float, nullable=True)
    package_special_instructions = Column(String, nullable=True)

    # Tracking information
    otp = Column(String, nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    rider_link = Column(String, nullable=True)
    customer_link = Column(String, nullable=True)
    is_tracking_active = Column(Boolean, default=False)
    location_history = Column(JSONB, default=list)  # List of locations

    # Timestamps
    estimated_delivery_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        """Convert model to dictionary for serialization"""
        return {
            "id": str(self.id),
            "tracking_id": self.tracking_id,
            "status": self.status,

            "vendor_id": str(self.vendor_id) if self.vendor_id else None,

            "customer": {
                "name": self.customer_name,
                "phone_number": self.customer_phone,
                "address": self.customer_address,
                "location": self.customer_location
            },

            "rider": {
                "id": str(self.rider_id) if self.rider_id else None,
                "name": self.rider_name,
                "phone_number": self.rider_phone,
                "current_location": self.rider_current_location
            },

            "package": {
                "description": self.package_description,
                "size": self.package_size,
                "weight": self.package_weight,
                "special_instructions": self.package_special_instructions
            },

            "tracking": {
                "otp": self.otp,
                "otp_expiry": self.otp_expiry.isoformat() if self.otp_expiry else None,
                "rider_link": self.rider_link,
                "customer_link": self.customer_link,
                "active": self.is_tracking_active,
                "location_history": self.location_history or []
            },

            "estimated_delivery_time": self.estimated_delivery_time.isoformat() if self.estimated_delivery_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }