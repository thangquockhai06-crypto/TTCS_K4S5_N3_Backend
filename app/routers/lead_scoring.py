"""
Router API cho phân hệ Cấu hình chấm điểm Lead (Lead Scoring - SCRUM-48 / Sprint 4).
Hỗ trợ:
- GET    /api/v1/leads/scoring/rules: Danh sách quy tắc chấm điểm (có lọc criteria_type, is_active).
- POST   /api/v1/leads/scoring/rules: Tạo mới một quy tắc chấm điểm (DIRECTOR, ADMIN).
- PUT    /api/v1/leads/scoring/rules/{rule_id}: Cập nhật quy tắc chấm điểm (DIRECTOR, ADMIN).
- DELETE /api/v1/leads/scoring/rules/{rule_id}: Xóa quy tắc chấm điểm (DIRECTOR, ADMIN).
- GET    /api/v1/leads/scoring/settings: Xem cấu hình ngưỡng nhiệt độ Hot/Warm/Cold.
- PUT    /api/v1/leads/scoring/settings: Cập nhật ngưỡng nhiệt độ Hot/Warm/Cold (DIRECTOR, ADMIN).
- POST   /api/v1/leads/scoring/recalculate-all: Tính lại điểm số hàng loạt cho toàn bộ Lead.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.lead_scoring import (
    ScoringRuleCreate,
    ScoringRuleUpdate,
    ScoringRuleResponse,
    ScoringSettingsUpdate,
    ScoringSettingsResponse,
    BatchRecalculateResponse,
)
from app.services.lead_scoring_service import LeadScoringService

router = APIRouter(prefix="/leads/scoring", tags=["Lead Scoring & Temperature (SCRUM-48 / Sprint 4)"])

SCORING_ADMIN_ROLES = {
    "director",
    "sales director",
    "vp of sales",
    "giám đốc kinh doanh",
    "admin",
    "super admin",
    "quản trị viên",
}


def require_scoring_admin_role(current_user: User = Depends(get_current_user)) -> User:
    """Xác thực người dùng có quyền quản trị quy tắc chấm điểm (Giám đốc kinh doanh hoặc Quản trị viên)."""
    role = (current_user.role or "").strip().lower()
    if role and role not in SCORING_ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền quản lý cấu hình chấm điểm Lead (Yêu cầu vai trò Giám đốc kinh doanh hoặc Quản trị viên).",
        )
    return current_user


# ==========================================
# A. Quản lý Cấu hình Quy tắc chấm điểm (Rules)
# ==========================================

@router.get(
    "/rules",
    response_model=List[ScoringRuleResponse],
    summary="Lấy danh sách các quy tắc chấm điểm Lead (SCRUM-48 AC1)",
)
def get_scoring_rules(
    criteria_type: Optional[str] = Query(None, description="Lọc theo nhóm tiêu chí: INDUSTRY, COMPANY_SIZE, SOURCE, INTEREST_LEVEL"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scoring_admin_role),
) -> List[ScoringRuleResponse]:
    """Danh sách toàn bộ quy tắc chấm điểm có hỗ trợ bộ lọc."""
    rules = LeadScoringService.get_rules(db=db, criteria_type=criteria_type, is_active=is_active)
    return [ScoringRuleResponse.model_validate(r) for r in rules]


@router.post(
    "/rules",
    response_model=ScoringRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mới một quy tắc chấm điểm Lead (SCRUM-48 AC1)",
)
def create_scoring_rule(
    rule_data: ScoringRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scoring_admin_role),
) -> ScoringRuleResponse:
    """Tạo mới quy tắc cộng/trừ điểm theo tiêu chí khai báo động."""
    rule = LeadScoringService.create_rule(db=db, rule_data=rule_data, current_user=current_user)
    return ScoringRuleResponse.model_validate(rule)


@router.put(
    "/rules/{rule_id}",
    response_model=ScoringRuleResponse,
    summary="Cập nhật quy tắc chấm điểm Lead (SCRUM-48 AC1)",
)
def update_scoring_rule(
    rule_id: str,
    rule_data: ScoringRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scoring_admin_role),
) -> ScoringRuleResponse:
    """Cập nhật tiêu chí, giá trị so sánh, điểm số hoặc trạng thái kích hoạt của quy tắc."""
    rule = LeadScoringService.update_rule(db=db, rule_id=rule_id, rule_data=rule_data, current_user=current_user)
    return ScoringRuleResponse.model_validate(rule)


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa một quy tắc chấm điểm Lead (SCRUM-48 AC1)",
)
def delete_scoring_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scoring_admin_role),
):
    """Xóa bỏ quy tắc chấm điểm theo ID."""
    LeadScoringService.delete_rule(db=db, rule_id=rule_id, current_user=current_user)
    return {"message": "Đã xóa quy tắc chấm điểm thành công.", "rule_id": rule_id}


# ==========================================
# B. Quản lý Cấu hình Ngưỡng nhiệt độ (Settings)
# ==========================================

@router.get(
    "/settings",
    response_model=ScoringSettingsResponse,
    summary="Lấy cấu hình ngưỡng nhiệt độ Hot/Warm/Cold hiện tại (SCRUM-48 AC2)",
)
def get_scoring_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scoring_admin_role),
) -> ScoringSettingsResponse:
    """Lấy ngưỡng phân loại nhiệt độ (Mặc định: HOT >= 70, WARM >= 40, COLD < 40)."""
    settings = LeadScoringService.get_or_create_settings(db)
    return ScoringSettingsResponse.model_validate(settings)


@router.put(
    "/settings",
    response_model=ScoringSettingsResponse,
    summary="Cập nhật cấu hình ngưỡng nhiệt độ Hot/Warm/Cold (SCRUM-48 AC2)",
)
def update_scoring_settings(
    update_data: ScoringSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scoring_admin_role),
) -> ScoringSettingsResponse:
    """Cập nhật ngưỡng nhiệt độ động do Giám đốc kinh doanh tùy chỉnh (Yêu cầu hot_threshold > warm_threshold)."""
    settings = LeadScoringService.update_settings(db=db, update_data=update_data, current_user=current_user)
    return ScoringSettingsResponse.model_validate(settings)


# ==========================================
# C. Tính toán lại Điểm số hàng loạt (Batch Recalculate)
# ==========================================

@router.post(
    "/recalculate-all",
    response_model=BatchRecalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Tính toán lại điểm số và nhiệt độ hàng loạt cho toàn bộ Lead (SCRUM-48 AC3)",
)
def recalculate_all_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scoring_admin_role),
) -> BatchRecalculateResponse:
    """
    Quét toàn bộ Lead đang hoạt động (chưa gộp status != 'MERGED'):
    - Chạy qua toàn bộ quy tắc đang kích hoạt (is_active = True).
    - So khớp ngưỡng nhiệt độ và cập nhật vào CSDL.
    - Trả về thống kê tổng số và phân loại từng nhóm Hot/Warm/Cold.
    """
    return LeadScoringService.recalculate_all_leads(db=db)
