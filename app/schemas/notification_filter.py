from pydantic import BaseModel, Field
from typing import Optional


class NotificationFilterParams(BaseModel):
    unreadOnly: bool = Field(False, description="Chỉ lấy thông báo chưa đọc")
    type: Optional[str] = Field(None, description="Lọc theo loại thông báo")
    targetType: Optional[str] = Field(None, description="Lọc theo đối tượng")
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=100)
