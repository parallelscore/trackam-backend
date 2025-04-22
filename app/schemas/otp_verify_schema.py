from typing import ClassVar
from pydantic import BaseModel, ConfigDict


class OTPVerifySchema(BaseModel):

    otp_code: str
    tracking_id: str


    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'otp_code': '123456',
                'tracking_id': 'TRK-12345678'
            }
        }
    )
