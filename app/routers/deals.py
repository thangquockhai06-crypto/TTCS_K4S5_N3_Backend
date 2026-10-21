from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.deal import Deal
from app.schemas.deal import (
    DealDTO,
    CreateDealDTO,
    UpdateDealDTO,
    MoveDealStageDTO,
    DealItemDTO,
    CreateDealItemDTO,
    CloseDealDTO,
    BulkReassignDealsDTO,
    SalesForecastDTO,
)
from app.schemas.deal_history import (
    DealHistoryListResponse,
    DealHistorySummaryResponse,
)
from app.services.deal_service import DealService
from app.core.export import export_to_excel

router = APIRouter(prefix="/deals", tags=["Deals Pipeline (EP-05: S5-01 -> S5-08)"])


# ==============================================================================
# S5-06 & S5-07: FORECAST & STALLED DEALS (Đặt trước /{deal_id} để tránh đụng URL)
# ==============================================================================

@router.get("/forecast", response_model=SalesForecastDTO, summary="Báo cáo dự báo doanh thu bán hàng theo trọng số xác suất (S5-06)")
def get_sales_forecast(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SalesForecastDTO:
    """
    S5-06: Dự báo doanh thu bán hàng:
    Weighted forecast = Sum of deal amount × stage win probability.
    Phân loại theo từng tháng, quý và từng giai đoạn phễu.
    """
    return DealService.get_sales_forecast(db=db, user=current_user)


@router.get("/stalled", response_model=List[DealDTO], summary="Danh sách các cơ hội bán hàng bị ứ đọng (S5-07)")
def get_stalled_deals(
    days: int = Query(14, ge=1, le=180, description="Ngưỡng số ngày không có hoạt động"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DealDTO]:
    """
    S5-07: Xác định các deal không có hoạt động trong X ngày hoặc quá hạn đóng hợp đồng.
    """
    return DealService.detect_and_get_stalled_deals(db=db, days_threshold=days, user=current_user)


@router.post("/scan-stalled", summary="Kích hoạt quét cơ hội ứ đọng (S5-07)")
def scan_stalled_deals(
    days: int = Query(14, ge=1, le=180, description="Ngưỡng số ngày không có hoạt động"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    S5-07: Quét và cập nhật cờ ứ đọng (is_stalled) cho tất cả các deal chưa đóng.
    Trả về số lượng deal đã quét và số lượng deal phát hiện bị ứ đọng.
    """
    return DealService.scan_stalled_deals(db=db, days_threshold=days, user=current_user)


@router.post("/bulk-reassign", summary="Tái phân bổ hàng loạt cơ hội bán hàng (alias)")
@router.post("/reassign", summary="Tái phân bổ hàng loạt cơ hội bán hàng cho người phụ trách mới (S5-08)")
def bulk_reassign_deals(
    dto: BulkReassignDealsDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    S5-08: Chuyển giao nhiều Deals cho chủ sở hữu mới kèm lý do bắt buộc và ghi lịch sử kiểm toán.
    """
    return DealService.bulk_reassign_deals(db=db, dto=dto, actor=current_user)


@router.get("/export", summary="Xuất danh sách cơ hội bán hàng ra Excel (.xlsx)")
def export_deals(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề"),
    stage: Optional[str] = Query(None, description="Lọc theo stage"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xuất danh sách deals ra Excel tuân thủ Data Scope."""
    deals = DealService.get_deals_for_export(
        db=db,
        user=current_user,
        search=search,
        stage=stage,
    )
    headers = ["Mã Deal", "Tiêu đề", "Giá trị (VNĐ)", "Giai đoạn (Stage)", "Xác suất (%)", "Mã KH", "Người phụ trách", "Ngày dự kiến đóng"]
    rows = [
        [
            d.id,
            d.title,
            float(d.value),
            d.stage,
            d.probability,
            d.customer_id,
            d.owner_id,
            d.expected_close_date.isoformat() if d.expected_close_date else "",
        ]
        for d in deals
    ]
    return export_to_excel(
        sheet_title="CoHoiBanHang",
        headers=headers,
        rows=rows,
        filename="danh_sach_co_hoi.xlsx",
    )


# ==============================================================================
# S5-01 & S5-02: DEAL LIST & KANBAN CRUD
# ==============================================================================

@router.get("", response_model=List[DealDTO], summary="Lấy danh sách các cơ hội bán hàng (S5-01 & S5-02)")
def get_deals(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề cơ hội"),
    stage: Optional[str] = Query(None, description="Lọc theo stage: lead, contact, proposal, negotiation, won, lost"),
    is_stalled: Optional[bool] = Query(None, description="Lọc deal ứ đọng"),
    campaign_id: Optional[str] = Query(None, description="Lọc theo chiến dịch"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DealDTO]:
    deals: List[Deal] = DealService.get_deals(
        db=db,
        user=current_user,
        search=search,
        stage=stage,
        is_stalled=is_stalled,
        campaign_id=campaign_id,
    )
    return [DealService.map_to_dto(d) for d in deals]


@router.post("", response_model=DealDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới cơ hội bán hàng (S5-01)")
def create_deal(
    dto: CreateDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    deal: Deal = DealService.create_deal(db=db, dto=dto, user=current_user)
    return DealService.map_to_dto(deal)


@router.get("/{deal_id}", response_model=DealDTO, summary="Xem chi tiết cơ hội bán hàng kèm sản phẩm (S5-01)")
def get_deal_detail(
    deal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    deal = DealService.get_deal_by_id(db=db, deal_id=deal_id, user=current_user)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy deal.")
    return DealService.map_to_dto(deal)


@router.put("/{deal_id}", response_model=DealDTO, summary="Cập nhật thông tin cơ hội bán hàng (S5-01)")
@router.patch("/{deal_id}", response_model=DealDTO, summary="Cập nhật thông tin cơ hội bán hàng (PATCH alias)")
def update_deal(
    deal_id: str,
    dto: UpdateDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    updated = DealService.update_deal(db=db, deal_id=deal_id, dto=dto, user=current_user)
    return DealService.map_to_dto(updated)


@router.get("/{deal_id}/history", response_model=DealHistoryListResponse, summary="Lấy danh sách lịch sử thay đổi của một cơ hội (SCRUM-91)")
def get_deal_history(
    deal_id: str,
    field_name: Optional[str] = Query(None, description="Tùy chọn lọc riêng theo: 'stage', 'amount', 'expected_close_date', 'assigned_to'"),
    start_date: Optional[str] = Query(None, description="Lọc thay đổi từ ngày (chuẩn YYYY-MM-DD hoặc ISO-8601)"),
    end_date: Optional[str] = Query(None, description="Lọc thay đổi đến ngày (chuẩn YYYY-MM-DD hoặc ISO-8601)"),
    changed_by: Optional[str] = Query(None, description="Lọc thay đổi theo người thực hiện (ID người dùng)"),
    page: int = Query(1, ge=1, description="Trang hiện tại (bắt đầu từ 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Số lượng bản ghi mỗi trang"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealHistoryListResponse:
    """
    SCRUM-91 (Sprint 5 / EP-05): Truy xuất lịch sử thay đổi của Cơ hội bán hàng (Deal Change History / Audit Log).
    - Phân quyền theo vai trò (Record-level Security):
      + DIRECTOR: Xem lịch sử của toàn bộ cơ hội trong hệ thống.
      + TEAM_LEAD: Xem lịch sử của các cơ hội thuộc nhân viên trong nhóm mình quản lý.
      + SALES_REP: Chỉ xem được lịch sử cơ hội do chính mình được giao phụ trách.
    """
    return DealService.get_deal_history(
        db=db,
        deal_id=deal_id,
        user=current_user,
        field_name=field_name,
        start_date=start_date,
        end_date=end_date,
        changed_by=changed_by,
        page=page,
        page_size=page_size,
    )


@router.get("/{deal_id}/history/summary", response_model=DealHistorySummaryResponse, summary="Thống kê tổng quan lịch sử thay đổi của một cơ hội (SCRUM-91)")
def get_deal_history_summary(
    deal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealHistorySummaryResponse:
    """
    SCRUM-91: Báo cáo tổng hợp các chỉ số thay đổi của cơ hội bán hàng.
    Bao gồm số lần đổi stage, đổi giá trị, thời điểm đầu/cuối và thống kê theo nhân viên.
    Phân quyền tương tự Record-level Security của Deal History.
    """
    return DealService.get_deal_history_summary(
        db=db,
        deal_id=deal_id,
        user=current_user,
    )


@router.post("/{deal_id}/stage", response_model=DealDTO, summary="Di chuyển stage của deal trên bảng Kanban (POST alias)")
@router.patch("/{deal_id}/stage", response_model=DealDTO, summary="Di chuyển stage của deal trên bảng Kanban kèm kiểm tra Exit Conditions (S5-02 & S5-04)")
def move_stage(
    deal_id: str,
    dto: MoveDealStageDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    """
    S5-02 & S5-04: Cập nhật giai đoạn phễu.
    Kiểm tra danh sách điều kiện thoát giai đoạn (Stage Requirements).
    Nếu không đạt và không có cờ override, hệ thống sẽ trả về lỗi 400 kèm lý do chi tiết.
    """
    deal = DealService.move_stage(
        db=db,
        deal_id=deal_id,
        new_stage=dto.stage,
        user=current_user,
        override=dto.override,
    )
    return DealService.map_to_dto(deal)


# ==============================================================================
# S5-03: PRODUCTS AND DEAL ITEMS
# ==============================================================================

@router.get("/{deal_id}/items", response_model=List[DealItemDTO], summary="Lấy danh sách sản phẩm thuộc cơ hội bán hàng (S5-03)")
def get_deal_items(
    deal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DealItemDTO]:
    deal = DealService.get_deal_by_id(db=db, deal_id=deal_id, user=current_user)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy deal.")
    return [
        DealItemDTO(
            id=i.id,
            dealId=i.deal_id,
            productId=i.product_id,
            productName=i.product_name,
            quantity=i.quantity,
            unitPrice=float(i.unit_price),
            discountPercent=float(i.discount_percent),
            billingCycle=i.billing_cycle,
            subtotal=float(i.subtotal),
        )
        for i in (deal.deal_items or [])
    ]


@router.post("/{deal_id}/items", response_model=DealItemDTO, status_code=status.HTTP_201_CREATED, summary="Thêm sản phẩm vào cơ hội bán hàng (S5-03)")
def add_deal_item(
    deal_id: str,
    dto: CreateDealItemDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealItemDTO:
    """
    S5-03: Thêm sản phẩm từ danh mục vào Deal.
    Hệ thống tự động tính subtotal và cập nhật lại tổng giá trị Deal authoritative trên backend.
    """
    item = DealService.add_deal_item(db=db, deal_id=deal_id, dto=dto, user=current_user)
    return DealItemDTO(
        id=item.id,
        dealId=item.deal_id,
        productId=item.product_id,
        productName=item.product_name,
        quantity=item.quantity,
        unitPrice=float(item.unit_price),
        discountPercent=float(item.discount_percent),
        billingCycle=item.billing_cycle,
        subtotal=float(item.subtotal),
    )


@router.delete("/{deal_id}/items/{item_id}", summary="Xóa sản phẩm khỏi cơ hội bán hàng (S5-03)")
def remove_deal_item(
    deal_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_value = DealService.remove_deal_item(db=db, deal_id=deal_id, item_id=item_id, user=current_user)
    return {"message": "Đã xóa dòng sản phẩm thành công.", "newDealValue": new_value}


# ==============================================================================
# S5-05: CLOSE WON / CLOSE LOST WORKFLOW
# ==============================================================================

@router.post("/{deal_id}/close", response_model=DealDTO, summary="Đóng cơ hội bán hàng Won hoặc Lost (S5-05)")
def close_deal(
    deal_id: str,
    dto: CloseDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    """
    S5-05: Đóng deal:
    - Nếu Won: yêu cầu giá trị ký thực tế và ngày ký kết hợp đồng.
    - Nếu Lost: yêu cầu lý do thất bại và đối thủ cạnh tranh.
    Ghi nhận lịch sử kiểm toán AuditLog đầy đủ.
    """
    return DealService.close_deal(db=db, deal_id=deal_id, dto=dto, user=current_user)
