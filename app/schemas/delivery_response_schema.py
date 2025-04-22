from typing import ClassVar, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.user_basic_schema import UserBasicSchema
from app.schemas.location_update_response_schema import LocationUpdateResponseSchema


class DeliveryResponseSchema(BaseModel):

    vendor: Optional[UserBasicSchema] = None
    driver: Optional[UserBasicSchema] = None
    customer: Optional[UserBasicSchema] = None
    latest_location: Optional[LocationUpdateResponseSchema] = None


    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'vendor': {
                    'id': 1,
                    'name': 'Vendor Name',
                    'phone': '+1234567890',
                    'role': 'vendor'
                },
                'driver': {
                    'id': 2,
                    'name': 'Driver Name',
                    'phone': '+0987654321',
                    'role': 'driver'
                },
                'customer': {
                    'id': 3,
                    'name': 'Customer Name',
                    'phone': '+1122334455',
                    'role': 'customer'
                },
                'latest_location': {
                    'id': 4,
                    'delivery_id': 5,
                    'created_at': "2023-10-01T12:00:00Z",
                    'updated_at': "2023-10-01T12:00:00Z"
                }
            }
        }
    )
