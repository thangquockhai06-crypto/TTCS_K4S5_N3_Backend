from typing import List, Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.export import export_to_excel
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
from app.services.deal_service import DealService
from app.services.saved_filter_service import SavedFilterService

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


@router.get("/export", summary="Xuất danh sách cơ hội bán hàng ra Excel (.xlsx) (S6-04)")
def export_deals(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề"),
    stage: Optional[str] = Query(None, description="Lọc theo stage"),
    min_value: Optional[float] = Query(None, description="Giá trị tối thiểu"),
    max_value: Optional[float] = Query(None, description="Giá trị tối đa"),
    close_date_from: Optional[date] = Query(None, description="Ngày dự kiến đóng từ ngày"),
    close_date_to: Optional[date] = Query(None, description="Ngày dự kiến đóng đến ngày"),
    owner_id: Optional[str] = Query(None, description="Lọc theo người phụ trách"),
    product_id: Optional[str] = Query(None, description="Lọc theo sản phẩm"),
    deal_ids: Optional[str] = Query(None, description="Danh sách ID các deal (phân cách bằng dấu phẩy)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xuất danh sách deals ra Excel tuân thủ Data Scope (S6-04). Hỗ trợ xuất tất cả hoặc theo deal được chọn."""
    selected_ids = [d.strip() for d in deal_ids.split(",") if d.strip()] if deal_ids else None
    deals = DealService.get_deals_for_export(
        db=db,
        user=current_user,
        search=search,
        stage=stage,
        min_value=min_value,
        max_value=max_value,
        close_date_from=close_date_from,
        close_date_to=close_date_to,
        owner_id=owner_id,
        product_id=product_id,
        deal_ids=selected_ids,
    )
    headers = [
        "Mã Deal",
        "Tiêu đề",
        "Giá trị (VNĐ)",
        "Giai đoạn (Stage)",
        "Xác suất (%)",
        "Tên Khách Hàng",
        "Người Phụ Trách",
        "Ngày dự kiến đóng",
        "Ngày đóng thực tế",
        "Doanh thu thực tế (VNĐ)",
        "Sản phẩm",
        "Trạng thái ứ đọng",
        "Ngày tạo",
    ]
    rows = [
        [
            d.id,
            d.title,
            float(d.value) if d.value is not None else 0.0,
            d.stage,
            d.probability,
            d.customer.full_name if d.customer else (d.customer_id or ""),
            d.owner.full_name if d.owner else (d.owner_id or ""),
            d.expected_close_date.isoformat() if d.expected_close_date else "",
            d.close_date.isoformat() if d.close_date else "",
            float(d.actual_value) if d.actual_value is not None else "",
            ", ".join([it.product_name for it in d.deal_items if it.product_name]) if d.deal_items else "",
            "Có" if d.is_stalled else "Không",
            d.created_at.strftime("%Y-%m-%d %H:%M:%S") if d.created_at else "",
        ]
        for deal in deals
    ]
    return export_to_excel(
        sheet_title="Deals",
        headers=["Deal ID", "Title", "Value", "Stage", "Outcome", "Actual value", "Signed date", "Lost reason", "Competitor", "Owner"],
        rows=rows,
        filename="danh_sach_deals.xlsx",
    )


# ==============================================================================
# S5-01, S5-02, S6-01, S6-02, S6-03: DEAL LIST & KANBAN CRUD
# ==============================================================================

@router.get("", response_model=List[DealDTO], summary="Lấy danh sách các cơ hội bán hàng (S6-01, S6-02, S6-03)")
def get_deals(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề cơ hội"),
    stage: Optional[str] = Query(None, description="Lọc theo stage: lead, contact, proposal, negotiation, won, lost"),
    is_stalled: Optional[bool] = Query(None, description="Lọc deal ứ đọng"),
    campaign_id: Optional[str] = Query(None, description="Lọc theo chiến dịch"),
    min_value: Optional[float] = Query(None, description="Lọc giá trị tối thiểu (S6-01, S6-02)"),
    max_value: Optional[float] = Query(None, description="Lọc giá trị tối đa (S6-01, S6-02)"),
    close_date_from: Optional[date] = Query(None, description="Lọc ngày đóng từ (S6-01, S6-02)"),
    close_date_to: Optional[date] = Query(None, description="Lọc ngày đóng đến (S6-01, S6-02)"),
    owner_id: Optional[str] = Query(None, description="Lọc theo người phụ trách (S6-01, S6-02, S6-03)"),
    product_id: Optional[str] = Query(None, description="Lọc theo sản phẩm (S6-02)"),
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
        min_value=min_value,
        max_value=max_value,
        close_date_from=close_date_from,
        close_date_to=close_date_to,
        owner_id=owner_id,
        product_id=product_id,
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
def update_deal(
    deal_id: str,
    dto: UpdateDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    updated = DealService.update_deal(db=db, deal_id=deal_id, dto=dto, user=current_user)
    return DealService.map_to_dto(updated)


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
