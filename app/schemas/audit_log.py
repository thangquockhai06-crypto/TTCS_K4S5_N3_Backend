from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, model_validator


class AuditLogSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    performed_by: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    action: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime
    timestamp: Optional[datetime] = None

    @model_validator(mode="after")
    def populate_timestamp(self) -> "AuditLogSchema":
        if self.timestamp is None:
            self.timestamp = self.created_at
        return self



class AuditLogPaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: List[AuditLogSchema]
    items: Optional[List[AuditLogSchema]] = None
    pages: Optional[int] = None

