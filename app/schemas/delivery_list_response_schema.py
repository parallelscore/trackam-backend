from typing import ClassVar, List
from pydantic import BaseModel, ConfigDict
from app.schemas.delivery_response_schema import DeliveryResponseSchema


class DeliveryListResponseSchema(BaseModel):

    items: List[DeliveryResponseSchema]
    total: int
    page: int
    size: int
    pages: int


    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'items': [
                    {
                        'id': 1,
                        'vendor_id': 1,
                        'driver_id': 2,
                        'customer_id': 3,
                        'tracking_id': 'unique-tracking-id',
                        'status': 'in_progress'
                    }
                ],
                'total': 100,
                'page': 1,
                'size': 10,
                'pages': 10
            }
        }
    )
