from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.quotation import QuotationDTO, PublicQuoteResponseDTO
from app.services.quotation_service import QuotationService

router = APIRouter(prefix="/public/quotes", tags=["Customer Quotation Portal (S7-06)"])


@router.get("/{access_token}", response_model=QuotationDTO, summary="Khách hàng xem báo giá qua đường dẫn riêng biệt (S7-06)")
def view_public_quote(
    access_token: str,
    db: Session = Depends(get_db),
) -> QuotationDTO:
    """
    S7-06: Khách hàng truy cập báo giá qua access link token mà không cần đăng nhập tài khoản CRM.
    Hệ thống tự động kiểm tra thời hạn và đánh dấu expired nếu quá hạn.
    """
    return QuotationService.get_public_quote(db=db, access_token=access_token)


@router.post("/{access_token}/respond", response_model=QuotationDTO, summary="Khách hàng Accept hoặc Reject báo giá trực tuyến (S7-06)")
def respond_public_quote(
    access_token: str,
    dto: PublicQuoteResponseDTO,
    db: Session = Depends(get_db),
) -> QuotationDTO:
    """
    S7-06: Khách hàng Chấp nhận hoặc Từ chối báo giá kèm ý kiến.
    Hệ thống lập tức cập nhật trạng thái báo giá, ghi nhận dòng thời gian cơ hội bán hàng,
    và gửi thông báo In-App cho chuyên viên phụ trách.
    """
    return QuotationService.respond_public_quote(
        db=db,
        access_token=access_token,
        action=dto.action,
        comment=dto.comment,
        signer_name=dto.signerName,
    )
