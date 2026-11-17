
from pydantic import BaseModel, Field
from typing import Optional


class DonorProfileCreate(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    donor_type: str = Field(min_length=2, max_length=50)
    license_number: Optional[str] = Field(default=None, max_length=100)
    address: str = Field(min_length=5)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=4, max_length=20)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
