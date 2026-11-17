
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, model_validator


class DonationCreate(BaseModel):
    category_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    food_type: Literal["VEG", "NON_VEG", "VEGAN"]
    quantity: float = Field(gt=0, le=100000)
    unit: str = Field(min_length=1, max_length=20)
    prepared_at: datetime
    expires_at: datetime
    storage_instructions: str = Field(min_length=2, max_length=100)
    packaging_type: str = Field(min_length=2, max_length=100)
    allergen_info: Optional[str] = None
    pickup_address: str = Field(min_length=5)
    pickup_city: str = Field(min_length=2, max_length=100)
    pickup_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    pickup_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    image_url: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_times(self):
        if self.expires_at <= self.prepared_at:
            raise ValueError("Expiry must be after preparation time.")
        return self
