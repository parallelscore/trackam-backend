from typing import ClassVar
from pydantic import BaseModel, ConfigDict
from app.api.models.user_model import UserRoleModel


class UserBasicSchema(BaseModel):

    id: int
    name: str
    phone: str
    role: UserRoleModel


    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'id': 1,
                'name': 'John Doe',
                'phone': '+1234567890',
                'role': UserRoleModel.DRIVER
            }
        }
    )
