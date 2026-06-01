from pydantic import BaseModel
from typing import Optional


class NotificationItem(BaseModel):
    id: int
    title: str
    content: str
    event_type: Optional[str] = None
    created_at: str
    is_read: bool


class NotificationListResponse(BaseModel):
    notifications: list[NotificationItem]


class UnreadCountResponse(BaseModel):
    count: int
