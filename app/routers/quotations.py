from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.quotation import Quotation
from app.schemas.quotation import QuotationDTO, CreateQuotationDTO
from app.schemas.catalog_item import QuotationLineDTO
from app.services.quotation_service import QuotationService
from app.core.export import export_to_excel

router = APIRouter(prefix="/quotations", tags=["Quotations Management"])


def _to_quotation_dto(quotation: Quotation) -> QuotationDTO:
    return QuotationDTO(
        id=quotation.id,
        quoteNumber=quotation.quote_number,
        title=quotation.title,
        customerId=quotation.customer_id,
        ownerId=quotation.owner_id,
        totalAmount=float(quotation.total_amount),
        status=quotation.status,
        validUntil=quotation.valid_until.isoformat() if quotation.valid_until else None,
        createdAt=quotation.created_at.isoformat() if quotation.created_at else None,
        items=[
            QuotationLineDTO.model_validate(line)
            for line in getattr(quotation, "lines", [])
        ],
        discount_approval_required=quotation.discount_approval_required,
    )


@router.get("", response_model=List[QuotationDTO], summary="Lấy danh sách các báo giá")
def get_quotations(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề hoặc mã báo giá"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: draft, sent, approved, rejected"),
    customerId: Optional[str] = Query(None, description="Lọc theo khách hàng"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[QuotationDTO]:
    quotations, _ = QuotationService.get_quotations(
        db=db,
        user=current_user,
        search=search,
        status=status,
        customer_id=customerId,
        skip=skip,
        limit=limit,
    )
    return [_to_quotation_dto(q) for q in quotations]


@router.get("/export", summary="Xuất danh sách báo giá ra Excel (.xlsx)")
def export_quotations(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề hoặc mã báo giá"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xuất danh sách báo giá ra Excel tuân thủ Data Scope."""
    quotations = QuotationService.get_quotations_for_export(
        db=db,
        user=current_user,
        search=search,
        status=status,
    )
    headers = ["Mã Báo Giá", "Số Báo Giá", "Tiêu đề", "Mã KH", "Người phụ trách", "Tổng tiền (VNĐ)", "Trạng thái", "Ngày tạo"]
    rows = [
        [
            q.id,
            q.quote_number,
            q.title,
            q.customer_id,
            q.owner_id,
            float(q.total_amount),
            q.status,
            q.created_at.strftime("%Y-%m-%d %H:%M:%S") if q.created_at else "",
        ]
        for q in quotations
    ]
    return export_to_excel(
        sheet_title="BaoGia",
        headers=headers,
        rows=rows,
        filename="danh_sach_bao_gia.xlsx",
    )


@router.post("", response_model=QuotationDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới báo giá")
def create_quotation(
    dto: CreateQuotationDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationDTO:
    quotation: Quotation = QuotationService.create_quotation(db=db, dto=dto, user=current_user)
    return _to_quotation_dto(quotation)


@router.get("/{quotation_id}", response_model=QuotationDTO, summary="Xem chi tiết báo giá")
def get_quotation_detail(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationDTO:
    quotation: Optional[Quotation] = QuotationService.get_quotation_by_id(
        db=db,
        quotation_id=quotation_id,
        user=current_user,
    )
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo giá.")
    return _to_quotation_dto(quotation)
