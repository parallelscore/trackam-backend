import uuid
from typing import ClassVar, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator


class DeliveryBaseSchema(BaseModel):

    package_info: str
    delivery_address: str
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    pickup_address: Optional[str] = None
    pickup_latitude: Optional[float] = None
    pickup_longitude: Optional[float] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
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
