from typing import ClassVar, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, field_validator


class CreateLocationUpdateSchema(BaseModel):

    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    altitude: Optional[float] = None
    battery_level: Optional[float] = None
    is_moving: Optional[bool] = True
    metadata: Optional[Dict[str, Any]] = None


    model_config: ClassVar = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'latitude': 12.345678,
                'longitude': 98.765432,
                'accuracy': 5.0,
                'speed': 50.0,
                'heading': 90.0,
                'altitude': 100.0,
                'battery_level': 85.0,
                'is_moving': True,
                'metadata': {'key': 'value'}
            }
        }
    )

    @field_validator('latitude')
    def validate_latitude(cls, v):
        if v < -90 or v > 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @field_validator('longitude')
    def validate_longitude(cls, v):
        if v < -180 or v > 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v

    @field_validator('battery_level')
    def validate_battery_level(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Battery level must be between 0 and 100')
        return v