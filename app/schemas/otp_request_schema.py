from uuid import UUID
from typing import ClassVar
from pydantic import BaseModel, ConfigDict


class OTPRequest(BaseModel):

    delivery_id: UUID
    phone: str
    role: str

    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'delivery_id': 'cd1aa8cc-bdbb-4459-b436-f47a12a9fac8',
                'phone': '+2341234567890',
                'role': 'rider'
            }
        }
    )
