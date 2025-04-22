import datetime
from uuid import UUID
from typing import ClassVar, Optional
from pydantic import BaseModel, ConfigDict


class Delivery(BaseModel):

    id: UUID
    vendor_name: Optional[str]
    rider_name: str
    rider_phone: str
    cust_name: str
    cust_phone: str
    package_desc: Optional[str]
    status: str
    created_at: datetime.datetime

    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'id': 'cd1aa8cc-bdbb-4459-b436-f47a12a9fac8',
                'vendor_name': 'Vendor Name',
                'rider_name': 'Rider Name',
                'rider_phone': '+2341234567890',
                'cust_name': 'Customer Name',
                'cust_phone': '+2340987654321',
                'package_desc': 'Package Description',
                'status': 'pending',
                'created_at': datetime.datetime.utcnow()
            }
        }
    )
