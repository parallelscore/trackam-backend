# app/api/models/delivery_model.py
import enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum, func

from app.utils.postgresql_db_util import db_util

base = db_util.base


class DeliveryStatusModel(str, enum.Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class DeliveryModel(base):

    __tablename__ = 'deliveries'
    __table_args__ = ({'schema': 'public'})

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(String, unique=True, index=True, nullable=False)

    # Relationships with users
    vendor_id = Column(Integer, ForeignKey("public.users.id"), nullable=False)
    vendor = relationship("UserModel", back_populates="vendor_deliveries", foreign_keys=[vendor_id])

    driver_id = Column(Integer, ForeignKey("public.users.id"), nullable=False)
    driver = relationship("UserModel", back_populates="driver_deliveries", foreign_keys=[driver_id])

    customer_id = Column(Integer, ForeignKey("public.users.id"), nullable=False)
    customer = relationship("UserModel", back_populates="customer_deliveries", foreign_keys=[customer_id])

    # Delivery details
    package_info = Column(Text, nullable=False)
    status = Column(Enum(DeliveryStatusModel), default=DeliveryStatusModel.CREATED, nullable=False)

    # Location data
    pickup_address = Column(String, nullable=True)
    pickup_latitude = Column(Float, nullable=True)
    pickup_longitude = Column(Float, nullable=True)

    delivery_address = Column(String, nullable=False)
    delivery_latitude = Column(Float, nullable=True)
    delivery_longitude = Column(Float, nullable=True)

    # Tracking data
    otp_code = Column(String, nullable=True)  # OTP for driver authentication
    otp_expires_at = Column(DateTime, nullable=True)
    driver_tracking_link = Column(String, nullable=True)
    customer_tracking_link = Column(String, nullable=True)

    # Timestamps for delivery stages
    assigned_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    in_transit_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Extra data
    notes = Column(Text, nullable=True)
    delivery_metadata = Column(JSONB, nullable=True)  # Additional flexible data

    # Locations relationship
    locations = relationship("LocationUpdateModel", back_populates="delivery", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


    def to_dict(self):
        """
        Convert the object to a dictionary.
        :return:
        """
        return {
            'id': self.id,
            'tracking_id': self.tracking_id,
            'vendor_id': self.vendor_id,
            'driver_id': self.driver_id,
            'customer_id': self.customer_id,
            'package_info': self.package_info,
            'status': self.status,
            'pickup_address': self.pickup_address,
            'pickup_latitude': self.pickup_latitude,
            'pickup_longitude': self.pickup_longitude,
            'delivery_address': self.delivery_address,
            'delivery_latitude': self.delivery_latitude,
            'delivery_longitude': self.delivery_longitude,
            'otp_code': self.otp_code,
            'otp_expires_at': self.otp_expires_at,
            'driver_tracking_link': self.driver_tracking_link,
            'customer_tracking_link': self.customer_tracking_link,
            'assigned_at': self.assigned_at,
            'accepted_at': self.accepted_at,
            'in_transit_at': self.in_transit_at,
            'delivered_at': self.delivered_at,
            'cancelled_at': self.cancelled_at,
            'notes': self.notes,
            'delivery_metadata': self.delivery_metadata,  # Fixed: was self.metadata
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f"<DeliveryModel id={self.id} tracking_id={self.tracking_id} vendor_id={self.vendor_id} driver_id={self.driver_id} customer_id={self.customer_id}>"
