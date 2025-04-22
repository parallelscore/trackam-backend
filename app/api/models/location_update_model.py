# app/api/models/location_update_model.py
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Integer, func, Float, DateTime, ForeignKey, Boolean

from app.utils.postgresql_db_util import db_util

base = db_util.base


class LocationUpdateModel(base):

    __tablename__ = 'location_updates'
    __table_args__ = ({'schema': 'public'})

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("public.deliveries.id"), nullable=False)
    delivery = relationship("DeliveryModel", back_populates="locations")

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)  # Location accuracy in meters
    speed = Column(Float, nullable=True)  # Speed in m/s
    heading = Column(Float, nullable=True)  # Heading in degrees
    altitude = Column(Float, nullable=True)  # Altitude in meters

    # Extra metadata about the location update
    battery_level = Column(Float, nullable=True)  # Battery percentage
    is_moving = Column(Boolean, default=True)
    location_update_metadata = Column(JSONB, nullable=True)  # Additional flexible data

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


    def to_dict(self):
        """
        Convert the object to a dictionary.
        :return:
        """
        return {
            'id': self.id,
            'delivery_id': self.delivery_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'speed': self.speed,
            'heading': self.heading,
            'altitude': self.altitude,
            'battery_level': self.battery_level,
            'is_moving': self.is_moving,
            'location_update_metadata': self.location_update_metadata,  # Fixed: was self.metadata
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f"<LocationUpdateModel delivery_id={self.delivery_id} lat={self.latitude} lng={self.longitude}>"
