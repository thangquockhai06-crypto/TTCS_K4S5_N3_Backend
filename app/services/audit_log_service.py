import math
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit_log import AuditLogPaginatedResponse, AuditLogSchema


class AuditLogService:
    def __init__(self, db: Session) -> None:
        self.repository = AuditLogRepository(db)

    def get_audit_logs(
        self,
        performed_by: Optional[str] = None,
        target_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 20,
    ) -> AuditLogPaginatedResponse:
        records, total_items = self.repository.get_audit_logs(
            performed_by=performed_by,
            target_type=target_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=limit,
        )

        data_dtos: List[AuditLogSchema] = [
            AuditLogSchema(
                id=str(rec.id),
                performed_by=str(rec.performed_by or rec.user_id or "system"),
                user_name=rec.user_name or "Người dùng hệ thống",
                user_email=rec.user_email or "",
                target_type=rec.target_type or "system",
                target_id=rec.target_id or "",
                field_name=rec.field_name or "",
                old_value=rec.old_value,
                new_value=rec.new_value,
                action=rec.action,
                details=rec.details,
                created_at=rec.created_at,
            )
            for rec in records
        ]

        pages = math.ceil(total_items / limit) if limit > 0 else 1
        return AuditLogPaginatedResponse(
            total=total_items,
            page=page,
            limit=limit,
            data=data_dtos,
            items=data_dtos,
            pages=pages,
        )
