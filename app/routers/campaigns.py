"""
Router API cho phân hệ Quản lý Chiến dịch Tiếp thị (Campaigns) - SCRUM-44 / Sprint 4.
Hỗ trợ:
- POST   /api/v1/campaigns     : Tạo chiến dịch tiếp thị mới (MARKETING, ADMIN, DIRECTOR).
- GET    /api/v1/campaigns     : Danh sách chiến dịch kèm các chỉ số thống kê tổng hợp (ROI, leads, deals, revenue).
- GET    /api/v1/campaigns/{id}: Chi tiết một chiến dịch kèm danh sách lead và deal liên kết.
- PUT    /api/v1/campaigns/{id}: Cập nhật thông tin chiến dịch.
- DELETE /api/v1/campaigns/{id}: Xóa chiến dịch an toàn (không xóa cascade mất lead/deal).
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignMetricsResponse,
    CampaignDetailResponse,
    CampaignListResponse,
)
from app.services.campaign_service import CampaignService

router = APIRouter(prefix="/campaigns", tags=["Marketing Campaigns Management (SCRUM-44 / Sprint 4)"])

CAMPAIGN_MUTATE_ROLES = {
    "marketing",
    "nhân viên marketing",
    "marketing staff",
    "director",
    "sales director",
    "vp of sales",
    "giám đốc kinh doanh",
    "admin",
    "super admin",
    "quản trị viên",
}


def require_campaign_mutate_role(current_user: User = Depends(get_current_user)) -> User:
    """Xác thực người dùng có quyền tạo/sửa/xóa Chiến dịch (MARKETING, ADMIN, DIRECTOR)."""
    role = (current_user.role or "").strip().lower()
    if role and role not in CAMPAIGN_MUTATE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thực hiện thao tác quản lý Chiến dịch (Yêu cầu vai trò Marketing, Director hoặc Admin).",
        )
    return current_user


@router.post(
    "",
    response_model=CampaignMetricsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Khai báo chiến dịch tiếp thị mới (SCRUM-44 AC1)",
)
def create_campaign(
    request: CampaignCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_mutate_role),
) -> CampaignMetricsResponse:
    """
    Tạo mới một chiến dịch Marketing:
    - Bắt buộc: name, channel, budget (>=0), start_date, end_date (>= start_date).
    - Status mặc định: 'ACTIVE'.
    - Yêu cầu vai trò: MARKETING, ADMIN, DIRECTOR.
    """
    camp = CampaignService.create_campaign(db=db, request=request, current_user=current_user)
    # Lấy thông tin kèm metrics ban đầu
    detail = CampaignService.get_campaign_detail(db=db, campaign_id=camp.id)
    return CampaignMetricsResponse.model_validate(detail)


@router.get(
    "",
    response_model=CampaignListResponse,
    summary="Danh sách chiến dịch kèm các chỉ số thống kê hiệu quả (SCRUM-44 AC3)",
)
def get_campaigns(
    status_filter: Optional[str] = Query(None, alias="status", description="Lọc theo trạng thái PLANNING/ACTIVE/COMPLETED/PAUSED"),
    channel: Optional[str] = Query(None, description="Lọc theo kênh tiếp thị"),
    search: Optional[str] = Query(None, description="Tìm theo tên hoặc mô tả"),
    start_date_from: Optional[date] = Query(None, description="Lọc ngày bắt đầu từ"),
    end_date_to: Optional[date] = Query(None, description="Lọc ngày kết thúc đến"),
    page: int = Query(1, ge=1, description="Số trang"),
    limit: int = Query(20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignListResponse:
    """
    Lấy danh sách chiến dịch kèm các chỉ số tính toán thời gian thực:
    - total_leads: Tổng số lead phát sinh từ chiến dịch.
    - total_deals: Tổng số cơ hội bán hàng.
    - won_deals_count: Số deal đã chốt thành công.
    - total_revenue: Tổng doanh thu đã chốt.
    - roi: Tỷ suất sinh lời sơ bộ so với ngân sách.
    """
    skip = (page - 1) * limit
    items, total = CampaignService.get_campaigns_with_metrics(
        db=db,
        status_filter=status_filter,
        channel=channel,
        search=search,
        start_date_from=start_date_from,
        end_date_to=end_date_to,
        skip=skip,
        limit=limit,
    )
    return CampaignListResponse(
        total=total,
        page=page,
        limit=limit,
        items=items,
    )


@router.get(
    "/{campaign_id}",
    response_model=CampaignDetailResponse,
    summary="Chi tiết chiến dịch kèm danh sách Leads và Deals (SCRUM-44 AC1 & AC2)",
)
def get_campaign_detail(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignDetailResponse:
    """Xem chi tiết chiến dịch và danh sách các lead, deal liên kết."""
    return CampaignService.get_campaign_detail(db=db, campaign_id=campaign_id)


@router.put(
    "/{campaign_id}",
    response_model=CampaignMetricsResponse,
    summary="Cập nhật thông tin chiến dịch (SCRUM-44 AC1)",
)
def update_campaign(
    campaign_id: str,
    request: CampaignUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_mutate_role),
) -> CampaignMetricsResponse:
    """Cập nhật thông tin/ngân sách/thời gian chạy chiến dịch."""
    camp = CampaignService.update_campaign(
        db=db,
        campaign_id=campaign_id,
        request=request,
        current_user=current_user,
    )
    detail = CampaignService.get_campaign_detail(db=db, campaign_id=camp.id)
    return CampaignMetricsResponse.model_validate(detail)


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa an toàn chiến dịch tiếp thị (SCRUM-44 AC1 & AC2)",
)
def delete_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_mutate_role),
):
    """
    Xóa chiến dịch tiếp thị an toàn:
    Tự động ngắt liên kết (SET NULL) trên Leads và Deals để không bị mất dữ liệu khách hàng.
    """
    CampaignService.delete_campaign(db=db, campaign_id=campaign_id, current_user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
