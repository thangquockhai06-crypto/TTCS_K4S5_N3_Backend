from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class NotificationDTO(BaseModel):
    id: str
    userId: str = Field(..., serialization_alias="userId")
    type: str
    title: str
    description: str
    targetType: Optional[str] = Field(None, serialization_alias="targetType")
    targetId: Optional[str] = Field(None, serialization_alias="targetId")
    linkUrl: Optional[str] = Field(None, serialization_alias="linkUrl")
    isRead: bool = Field(False, serialization_alias="isRead")
    createdAt: str = Field(..., serialization_alias="createdAt")
    timeAgo: Optional[str] = Field(None, serialization_alias="timeAgo")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CreateNotificationDTO(BaseModel):
    userId: str = Field(..., serialization_alias="userId")
    type: str
    title: str
    description: str
    targetType: Optional[str] = Field(None, serialization_alias="targetType")
    targetId: Optional[str] = Field(None, serialization_alias="targetId")
    linkUrl: Optional[str] = Field(None, serialization_alias="linkUrl")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class NotificationListResponseDTO(BaseModel):
    items: List[NotificationDTO]
    unreadCount: int = Field(0, serialization_alias="unreadCount")
    total: int = 0

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
