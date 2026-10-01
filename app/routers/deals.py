from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.deal import Deal
from app.schemas.deal import DealDTO, CreateDealDTO, MoveDealStageDTO
from app.services.deal_service import DealService
from app.core.export import export_to_excel

router = APIRouter(prefix="/deals", tags=["Deals Pipeline (Kanban)"])


@router.get("", response_model=List[DealDTO], summary="Lấy danh sách các cơ hội bán hàng")
def get_deals(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề cơ hội"),
    stage: Optional[str] = Query(None, description="Lọc theo stage: lead, contact, proposal, negotiation, won, lost"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DealDTO]:
    deals: List[Deal] = DealService.get_deals(
        db=db,
        user=current_user,
        search=search,
        stage=stage,
    )
    return [
        DealDTO(
            id=d.id,
            title=d.title,
            value=float(d.value),
            stage=d.stage,
            probability=d.probability,
            customerId=d.customer_id,
            ownerId=d.owner_id,
            expectedCloseDate=d.expected_close_date.isoformat() if d.expected_close_date else None,
            createdAt=d.created_at.isoformat() if d.created_at else None,
        )
        for d in deals
    ]


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


@router.post("", response_model=DealDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới cơ hội bán hàng")
def create_deal(
    dto: CreateDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    deal: Deal = DealService.create_deal(db=db, dto=dto, user=current_user)
    return DealDTO(
        id=deal.id,
        title=deal.title,
        value=float(deal.value),
        stage=deal.stage,
        probability=deal.probability,
        customerId=deal.customer_id,
        ownerId=deal.owner_id,
        expectedCloseDate=deal.expected_close_date.isoformat() if deal.expected_close_date else None,
        createdAt=deal.created_at.isoformat() if deal.created_at else None,
    )


@router.get("/{deal_id}", response_model=DealDTO, summary="Xem chi tiết cơ hội bán hàng")
def get_deal_detail(
    deal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    deal: Optional[Deal] = DealService.get_deal_by_id(db=db, deal_id=deal_id, user=current_user)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy deal.")
    return DealDTO(
        id=deal.id,
        title=deal.title,
        value=float(deal.value),
        stage=deal.stage,
        probability=deal.probability,
        customerId=deal.customer_id,
        ownerId=deal.owner_id,
        expectedCloseDate=deal.expected_close_date.isoformat() if deal.expected_close_date else None,
        createdAt=deal.created_at.isoformat() if deal.created_at else None,
    )


@router.patch("/{deal_id}/stage", response_model=DealDTO, summary="Di chuyển stage của deal trên bảng Kanban")
def move_stage(
    deal_id: str,
    dto: MoveDealStageDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    deal: Optional[Deal] = DealService.move_stage(
        db=db,
        deal_id=deal_id,
        new_stage=dto.stage,
        user=current_user,
    )
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy deal.")
    return DealDTO(
        id=deal.id,
        title=deal.title,
        value=float(deal.value),
        stage=deal.stage,
        probability=deal.probability,
        customerId=deal.customer_id,
        ownerId=deal.owner_id,
        expectedCloseDate=deal.expected_close_date.isoformat() if deal.expected_close_date else None,
        createdAt=deal.created_at.isoformat() if deal.created_at else None,
    )
