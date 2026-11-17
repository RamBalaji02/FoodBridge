from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    user_id: int = Field(gt=0)
    title: str = Field(min_length=2, max_length=200)
    message: str = Field(min_length=1)
    notification_type: str = Field(min_length=2, max_length=50)