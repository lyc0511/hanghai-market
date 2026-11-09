from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    body: str | None
    link: str | None
    is_read: bool
    created_at: datetime


class UnreadCountOut(BaseModel):
    count: int
