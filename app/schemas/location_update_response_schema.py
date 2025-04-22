from typing import ClassVar
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class LocationUpdateResponseSchema(BaseModel):

    id: int
    delivery_id: int
    created_at: datetime
    updated_at: datetime


    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'id': 1,
                'delivery_id': 2,
                'created_at': "2023-10-01T12:00:00Z",
                'updated_at': "2023-10-01T12:00:00Z"
            }
        }
    )
