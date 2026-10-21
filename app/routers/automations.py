from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.automation import (
    AutomationRuleDTO,
    CreateAutomationRuleDTO,
    UpdateAutomationRuleDTO,
    AutomationLogDTO,
)
from app.services.automation_service import AutomationService

router = APIRouter(prefix="/automations", tags=["Automation Rules Engine (S7-09)"])


@router.get("", response_model=List[AutomationRuleDTO], summary="Lấy danh sách các quy tắc tự động hóa IF–THEN (S7-09)")
def get_automation_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AutomationRuleDTO]:
    rules, _ = AutomationService.get_rules(db=db, skip=skip, limit=limit)
    return rules


@router.post("", response_model=AutomationRuleDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới quy tắc tự động hóa (S7-09)")
def create_automation_rule(
    dto: CreateAutomationRuleDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AutomationRuleDTO:
    return AutomationService.create_rule(db=db, dto=dto)


@router.patch("/{rule_id}/toggle", response_model=AutomationRuleDTO, summary="Bật / Tắt quy tắc tự động hóa (S7-09)")
def toggle_automation_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AutomationRuleDTO:
    return AutomationService.toggle_rule(db=db, rule_id=rule_id)


@router.delete("/{rule_id}", summary="Xóa quy tắc tự động hóa (S7-09)")
def delete_automation_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    AutomationService.delete_rule(db=db, rule_id=rule_id)
    return {"success": True, "message": "Đã xóa quy tắc tự động hóa thành công."}


@router.get("/logs", response_model=List[AutomationLogDTO], summary="Lấy nhật ký thực thi các quy tắc tự động hóa (S7-09)")
def get_automation_logs(
    ruleId: Optional[str] = Query(None, description="Lọc theo quy tắc cụ thể"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AutomationLogDTO]:
    logs, _ = AutomationService.get_logs(db=db, rule_id=ruleId, skip=skip, limit=limit)
    return logs
