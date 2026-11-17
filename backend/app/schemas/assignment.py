
from typing import Literal, Optional
from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    request_id: int = Field(gt=0)
    volunteer_id: int = Field(gt=0)


class AssignmentStatusUpdate(BaseModel):
    action: Literal["ACCEPT", "PICKUP", "IN_TRANSIT", "DELIVER"]
    otp: Optional[str] = Field(
        default=None,
        min_length=6,
        max_length=6
    )
    notes: Optional[str] = Field(default=None, max_length=1000)
