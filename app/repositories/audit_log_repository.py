from datetime import datetime
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db: Session = db

    def get_audit_logs(
        self,
        performed_by: Optional[str] = None,
        target_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[AuditLog], int]:
        query = self.db.query(AuditLog)

        if performed_by:
            user_pattern: str = f"%{performed_by.strip()}%"
            query = query.filter(
                or_(
                    AuditLog.performed_by.ilike(user_pattern),
                    AuditLog.user_name.ilike(user_pattern),
                    AuditLog.user_email.ilike(user_pattern),
                )
            )

        if target_type and target_type.lower() != "all":
            query = query.filter(AuditLog.target_type == target_type.lower())

        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)

        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        total_items: int = query.count()
        offset_val: int = (page - 1) * limit
        records: List[AuditLog] = (
            query.order_by(AuditLog.created_at.desc())
            .offset(offset_val)
            .limit(limit)
            .all()
        )

        return records, total_items

    def create_audit_log(self, audit_log: AuditLog) -> AuditLog:
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        return audit_log
