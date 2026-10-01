from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


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



class AuditLogPaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: List[AuditLogSchema]
