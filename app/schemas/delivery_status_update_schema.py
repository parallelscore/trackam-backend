from typing import ClassVar
from pydantic import BaseModel, ConfigDict

from app.api.models.delivery_model import DeliveryStatusModel


class DeliveryStatusUpdateSchema(BaseModel):

    tracking_id: str
    status: DeliveryStatusModel


    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'tracking_id': 'TRK-12345678',
                'status': 'delivered'
            }
        }
    )
