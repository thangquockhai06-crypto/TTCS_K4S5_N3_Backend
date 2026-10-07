from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.win_loss import WinLossReason, Competitor
from app.schemas.win_loss import (
    WinLossReasonDTO,
    CreateWinLossReasonDTO,
    CompetitorDTO,
    CreateCompetitorDTO,
)

router = APIRouter(prefix="/win-loss-config", tags=["Win/Loss Reasons & Competitors (S2-10)"])


# --- 1. Win/Loss Reasons ---
@router.get("/reasons", response_model=List[WinLossReasonDTO], summary="Lấy danh sách lý do Thắng / Thua cơ hội")
def get_win_loss_reasons(
    resultType: Optional[str] = Query(None, description="Lọc theo loại: WON | LOST"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[WinLossReasonDTO]:
    # Pre-populate defaults if empty
    if db.query(WinLossReason).count() == 0:
        defaults = [
            WinLossReason(
                result_type="WON",
                code="PRICE_COMPETITIVE",
                reason="Giá cả & Chính sách chiết khấu vượt trội",
                description="Báo giá cạnh tranh hơn đối thủ từ 10-15%",
            ),
            WinLossReason(
                result_type="WON",
                code="TECH_SUPERIOR",
                reason="Giải pháp công nghệ đáp ứng 100% yêu cầu",
                description="Tích hợp trơn tru với hệ thống Core của khách hàng",
            ),
            WinLossReason(
                result_type="WON",
                code="TRUST_REPUTATION",
                reason="Uy tín thương hiệu & Dịch vụ bảo hành tin cậy",
                description="Cam kết SLA 99.9% hỗ trợ 24/7",
            ),
            WinLossReason(
                result_type="LOST",
                code="HIGH_BUDGET",
                reason="Vượt quá ngân sách dự kiến của khách hàng",
                description="Khách hàng chưa đủ ngân sách trong năm tài chính này",
            ),
            WinLossReason(
                result_type="LOST",
                code="LOST_TO_COMPETITOR",
                reason="Thua đối thủ cạnh tranh trực tiếp",
                description="Đối thủ giảm giá sâu hoặc có quan hệ thân thiết",
            ),
            WinLossReason(
                result_type="LOST",
                code="PROJECT_CANCELLED",
                reason="Dự án bị hoãn / Hủy kế hoạch mua sắm",
                description="Thay đổi định hướng nội bộ của ban lãnh đạo khách hàng",
            ),
        ]
        db.add_all(defaults)
        db.commit()

    query = db.query(WinLossReason)
    if resultType and resultType.upper() in ["WON", "LOST"]:
        query = query.filter(WinLossReason.result_type == resultType.upper())
    records = query.order_by(WinLossReason.result_type.desc(), WinLossReason.created_at.asc()).all()

    return [
        WinLossReasonDTO(
            id=r.id,
            result_type=r.result_type,
            code=r.code,
            reason=r.reason,
            description=r.description,
            is_active=r.is_active,
        )
        for r in records
    ]


@router.post("/reasons", response_model=WinLossReasonDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới lý do Thắng/Thua")
def create_win_loss_reason(
    dto: CreateWinLossReasonDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WinLossReasonDTO:
    reason = WinLossReason(
        result_type=dto.result_type.upper(),
        code=dto.code.strip().upper(),
        reason=dto.reason.strip(),
        description=dto.description,
    )
    db.add(reason)
    db.commit()
    db.refresh(reason)
    return WinLossReasonDTO(
        id=reason.id,
        result_type=reason.result_type,
        code=reason.code,
        reason=reason.reason,
        description=reason.description,
        is_active=reason.is_active,
    )


@router.delete("/reasons/{reason_id}", summary="Xóa lý do Thắng/Thua")
def delete_win_loss_reason(
    reason_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = db.query(WinLossReason).filter(WinLossReason.id == reason_id).first()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lý do.")
    db.delete(r)
    db.commit()
    return {"message": "Đã xóa lý do thành công."}


# --- 2. Competitors ---
@router.get("/competitors", response_model=List[CompetitorDTO], summary="Lấy danh sách đối thủ cạnh tranh")
def get_competitors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CompetitorDTO]:
    records = db.query(Competitor).order_by(Competitor.created_at.asc()).all()

    if not records:
        defaults = [
            Competitor(
                name="SalesForce Enterprise",
                website="https://www.salesforce.com",
                strengths="Hệ sinh thái ứng dụng phong phú, danh tiếng toàn cầu",
                weaknesses="Chi phí triển khai rất đắt, tùy biến phức tạp, hỗ trợ tiếng Việt kém",
                win_rate=42.5,
            ),
            Competitor(
                name="HubSpot CRM Pro",
                website="https://www.hubspot.com",
                strengths="Marketing Automation tốt, giao diện thân thiện",
                weaknesses="Chi phí tăng phi mã theo số lượng contact, thiếu phân quyền sâu",
                win_rate=58.0,
            ),
            Competitor(
                name="Zoho CRM Plus",
                website="https://www.zoho.com",
                strengths="Giá rẻ, nhiều tính năng",
                weaknesses="Trải nghiệm người dùng rời rạc, server đôi khi chậm ở VN",
                win_rate=65.0,
            ),
        ]
        db.add_all(defaults)
        db.commit()
        records = db.query(Competitor).all()

    return [
        CompetitorDTO(
            id=c.id,
            name=c.name,
            website=c.website,
            strengths=c.strengths,
            weaknesses=c.weaknesses,
            win_rate=float(c.win_rate),
        )
        for c in records
    ]


@router.post("/competitors", response_model=CompetitorDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới đối thủ cạnh tranh")
def create_competitor(
    dto: CreateCompetitorDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompetitorDTO:
    comp = Competitor(
        name=dto.name.strip(),
        website=dto.website.strip() if dto.website else None,
        strengths=dto.strengths,
        weaknesses=dto.weaknesses,
        win_rate=dto.win_rate or 50.0,
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return CompetitorDTO(
        id=comp.id,
        name=comp.name,
        website=comp.website,
        strengths=comp.strengths,
        weaknesses=comp.weaknesses,
        win_rate=float(comp.win_rate),
    )


@router.delete("/competitors/{competitor_id}", summary="Xóa đối thủ cạnh tranh")
def delete_competitor(
    competitor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = db.query(Competitor).filter(Competitor.id == competitor_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đối thủ.")
    db.delete(c)
    db.commit()
    return {"message": "Đã xóa đối thủ cạnh tranh thành công."}
