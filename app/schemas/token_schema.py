from typing import ClassVar
from pydantic import BaseModel, ConfigDict


class OTPRequest(BaseModel):

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'access_token': 'cd1aa8cc-bdbb-4459-b436-f47a12a9fac8',
                'token_type': 'bearer',
                'expires_in': 3600
            }
        }
    )
