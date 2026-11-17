from pydantic import BaseModel, Field


class DonationRequestCreate(BaseModel):
    donation_id: int = Field(gt=0)
    requested_quantity: float = Field(gt=0, le=100000)
    message: str | None = Field(default=None, max_length=500)

from typing import Literal

from pydantic import BaseModel, Field


class DonationRequestRespond(BaseModel):
    action: Literal["ACCEPT", "REJECT"]
    rejection_reason: str | None = Field(default=None, max_length=500)