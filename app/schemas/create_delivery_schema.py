import uuid
from typing import ClassVar, Optional
from pydantic import ConfigDict, field_validator

from app.schemas.delivery_base_schema import DeliveryBaseSchema


class CreateDeliverySchema(DeliveryBaseSchema):

    vendor_id: Optional[int] = None  # If not provided, use authenticated user
    driver_id: int
    customer_id: int

    # You might want these to be filled automatically, but this gives flexibility
    tracking_id: Optional[str] = None


    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'vendor_id': 1,
                'driver_id': 2,
                'customer_id': 3,
                'package_info': 'Electronics',
                'delivery_address': '123 Main St, Springfield',
                'delivery_latitude': 37.7749,
                'delivery_longitude': -122.4194,
                'pickup_address': '456 Elm St, Springfield',
                'pickup_latitude': 37.7749,
                'pickup_longitude': -122.4194,
                'notes': 'Handle with care',
                'metadata': {'order_id': 12345}
            }
        }
    )

    @classmethod
    @field_validator('tracking_id', mode='before')
    def set_tracking_id(cls, v):
        return v or f"TRK-{uuid.uuid4().hex[:8].upper()}"
