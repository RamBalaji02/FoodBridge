
from typing import Optional
from pydantic import BaseModel, Field


class VolunteerProfileCreate(BaseModel):
    vehicle_type: str = Field(min_length=2, max_length=50)
    vehicle_number: Optional[str] = Field(
        default=None, max_length=50
    )
    city: str = Field(min_length=2, max_length=100)
    emergency_contact: str = Field(
        min_length=10, max_length=20
    )


class VolunteerAvailabilityUpdate(BaseModel):
    is_available: bool
