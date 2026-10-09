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
    UpdateWinLossReasonDTO,
    CompetitorDTO,
    CreateCompetitorDTO,
    UpdateCompetitorDTO,
)

router = APIRouter(prefix="/win-loss-config", tags=["Win/Loss Reasons & Competitors (S2-10 / SCRUM-89)"])


# ==============================================================================
# 1. Quản lý Danh mục Lý do Thắng / Thua (Win/Loss Reasons)
# ==============================================================================

def _seed_default_reasons(db: Session) -> None:
    """Nạp dữ liệu lý do mẫu ban đầu nếu bảng đang rỗng."""
    if db.query(WinLossReason).count() == 0:
        defaults = [
            # WON
            WinLossReason(
                result_type="WON",
                code="PRICE_COMPETITIVE",
                reason="Chính sách giá & Chiết khấu cạnh tranh vượt trội",
                description="Báo giá tốt hơn đối thủ từ 10-15% kèm chính sách trả góp linh hoạt",
                is_active=True,
                usage_count=48,
            ),
            WinLossReason(
                result_type="WON",
                code="FEATURE_RICH",
                reason="Tính năng phân quyền & Tùy biến đa cấp đáp ứng 100% nghiệp vụ",
                description="Khách hàng đánh giá rất cao phân hệ trường tùy chỉnh và sơ đồ cây phòng ban",
                is_active=True,
                usage_count=36,
            ),
            WinLossReason(
                result_type="WON",
                code="SUPPORT_EXCELLENT",
                reason="Dịch vụ Onboarding & Hỗ trợ kỹ thuật 24/7 tận tâm",
                description="Cam kết SLA phản hồi dưới 15 phút và hỗ trợ trực tiếp tại doanh nghiệp",
                is_active=True,
                usage_count=24,
            ),
            # LOST
            WinLossReason(
                result_type="LOST",
                code="BUDGET_CUT",
                reason="Khách hàng cắt giảm ngân sách đầu tư CNTT năm nay",
                description="Dự án bị hoãn sang quý sau do biến động kinh doanh nội bộ khách hàng",
                is_active=True,
                usage_count=19,
            ),
            WinLossReason(
                result_type="LOST",
                code="CHOSE_COMPETITOR",
                reason="Khách hàng chọn đối thủ có giá thành thấp hơn",
                description="Khách hàng chấp nhận giải pháp ít tính năng hơn để tiết kiệm chi phí ban đầu",
                is_active=True,
                usage_count=14,
            ),
            WinLossReason(
                result_type="LOST",
                code="INTERNAL_BUILD",
                reason="Khách hàng quyết định tự xây dựng phần mềm nội bộ (In-house)",
                description="Đội ngũ IT nội bộ của khách hàng tiếp quản dự án",
                is_active=True,
                usage_count=5,
            ),
        ]
        db.add_all(defaults)
        db.commit()

    required_lost_reasons = [
        ("PRICE_TOO_HIGH", "Giá quá cao", "Giá đề xuất vượt ngân sách hoặc kỳ vọng của khách hàng."),
        ("NO_DECISION", "Không có quyết định", "Khách hàng không ra quyết định trong thời hạn dự kiến."),
        ("BAD_TIMING", "Thời điểm không phù hợp", "Ngân sách hoặc ưu tiên của khách hàng chưa phù hợp."),
        ("PRODUCT_GAP", "Thiếu tính năng sản phẩm", "Sản phẩm chưa đáp ứng một yêu cầu quan trọng."),
        ("OTHER", "Khác", "Lý do khác; bắt buộc ghi chú chi tiết."),
    ]
    existing_codes = {
        code
        for (code,) in db.query(WinLossReason.code)
        .filter(WinLossReason.result_type == "LOST")
        .all()
    }
    missing = [
        WinLossReason(
            result_type="LOST",
            code=code,
            reason=reason,
            description=description,
            is_active=True,
            usage_count=0,
        )
        for code, reason, description in required_lost_reasons
        if code not in existing_codes
    ]
    if missing:
        db.add_all(missing)
        db.commit()


@router.get(
    "/reasons",
    response_model=List[WinLossReasonDTO],
    summary="Lấy danh sách lý do Thắng / Thua cơ hội",
)
def get_win_loss_reasons(
    resultType: Optional[str] = Query(None, description="Lọc theo loại: WON | LOST | all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[WinLossReasonDTO]:
    _seed_default_reasons(db)

    query = db.query(WinLossReason)
    if resultType and resultType.upper() in ["WON", "LOST"]:
        query = query.filter(WinLossReason.result_type == resultType.upper())

    records = query.order_by(
        WinLossReason.result_type.desc(),  # WON xếp trước, LOST xếp sau
        WinLossReason.created_at.asc(),
    ).all()

    return [
        WinLossReasonDTO(
            id=r.id,
            result_type=r.result_type,
            code=r.code,
            reason=r.reason,
            description=r.description,
            is_active=r.is_active,
            usage_count=r.usage_count,
        )
        for r in records
    ]


@router.post(
    "/reasons",
    response_model=WinLossReasonDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mới lý do Thắng / Thua",
)
def create_win_loss_reason(
    dto: CreateWinLossReasonDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WinLossReasonDTO:
    clean_code = dto.code.strip().upper()
    existing = db.query(WinLossReason).filter(WinLossReason.code == clean_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã lý do '{clean_code}' đã tồn tại trong hệ thống.",
        )

    reason = WinLossReason(
        result_type=dto.result_type.strip().upper(),
        code=clean_code,
        reason=dto.reason.strip(),
        description=dto.description.strip() if dto.description else None,
        is_active=dto.is_active if dto.is_active is not None else True,
        usage_count=0,
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
        usage_count=reason.usage_count,
    )


@router.put(
    "/reasons/{reason_id}",
    response_model=WinLossReasonDTO,
    summary="Cập nhật thông tin lý do Thắng / Thua",
)
def update_win_loss_reason(
    reason_id: str,
    dto: UpdateWinLossReasonDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WinLossReasonDTO:
    r = db.query(WinLossReason).filter(WinLossReason.id == reason_id).first()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lý do cần cập nhật.",
        )

    if dto.code is not None:
        clean_code = dto.code.strip().upper()
        conflict = (
            db.query(WinLossReason)
            .filter(WinLossReason.code == clean_code, WinLossReason.id != reason_id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã lý do '{clean_code}' đã được sử dụng bởi mục khác.",
            )
        r.code = clean_code

    if dto.result_type is not None:
        r.result_type = dto.result_type.strip().upper()

    if dto.reason is not None:
        r.reason = dto.reason.strip()

    if dto.description is not None:
        r.description = dto.description.strip() if dto.description else None

    if dto.is_active is not None:
        r.is_active = dto.is_active

    db.commit()
    db.refresh(r)

    return WinLossReasonDTO(
        id=r.id,
        result_type=r.result_type,
        code=r.code,
        reason=r.reason,
        description=r.description,
        is_active=r.is_active,
        usage_count=r.usage_count,
    )


@router.delete(
    "/reasons/{reason_id}",
    summary="Xóa lý do Thắng / Thua",
)
def delete_win_loss_reason(
    reason_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = db.query(WinLossReason).filter(WinLossReason.id == reason_id).first()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lý do cần xóa.",
        )

    deleted_title = r.reason
    db.delete(r)
    db.commit()

    return {"message": f"Đã xóa lý do '{deleted_title}' thành công."}


# ==============================================================================
# 2. Quản lý Danh mục Đối thủ Cạnh tranh (Competitors)
# ==============================================================================

def _seed_default_competitors(db: Session) -> None:
    """Nạp dữ liệu đối thủ cạnh tranh mẫu ban đầu nếu bảng đang rỗng."""
    if db.query(Competitor).count() == 0:
        defaults = [
            Competitor(
                name="Salesforce CRM Enterprise",
                website="https://www.salesforce.com",
                pricing_tier="Rất cao (2.500.000đ/user/tháng)",
                strengths="Thương hiệu toàn cầu, hệ sinh thái AppExchange phong phú",
                weaknesses="Chi phí triển khai cực kỳ đắt đỏ, giao diện tiếng Anh khó sử dụng",
                win_rate=68.0,
                is_active=True,
            ),
            Competitor(
                name="HubSpot Sales Hub",
                website="https://www.hubspot.com",
                pricing_tier="Trung bình - Cao (1.200.000đ/user/tháng)",
                strengths="Marketing Automation mạnh mẽ, giao diện trực quan",
                weaknesses="Tính năng phân quyền sâu và quản lý giá sàn còn hạn chế",
                win_rate=74.0,
                is_active=True,
            ),
            Competitor(
                name="Zoho CRM Plus",
                website="https://www.zoho.com",
                pricing_tier="Trung bình (650.000đ/user/tháng)",
                strengths="Nhiều phân hệ tích hợp, chi phí bản quyền ban đầu cạnh tranh",
                weaknesses="Tốc độ tải chậm tại Việt Nam, quy trình tùy biến phễu phức tạp",
                win_rate=82.0,
                is_active=True,
            ),
        ]
        db.add_all(defaults)
        db.commit()


@router.get(
    "/competitors",
    response_model=List[CompetitorDTO],
    summary="Lấy danh sách đối thủ cạnh tranh",
)
def get_competitors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CompetitorDTO]:
    _seed_default_competitors(db)

    records = db.query(Competitor).order_by(Competitor.created_at.asc()).all()

    return [
        CompetitorDTO(
            id=c.id,
            name=c.name,
            website=c.website,
            pricing_tier=c.pricing_tier or "Trung cấp",
            strengths=c.strengths,
            weaknesses=c.weaknesses,
            win_rate=float(c.win_rate) if c.win_rate is not None else 50.0,
            is_active=c.is_active,
        )
        for c in records
    ]


@router.post(
    "/competitors",
    response_model=CompetitorDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mới đối thủ cạnh tranh",
)
def create_competitor(
    dto: CreateCompetitorDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompetitorDTO:
    clean_name = dto.name.strip()
    existing = db.query(Competitor).filter(Competitor.name == clean_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Đối thủ cạnh tranh '{clean_name}' đã tồn tại trong hệ thống.",
        )

    comp = Competitor(
        name=clean_name,
        website=dto.website.strip() if dto.website else None,
        pricing_tier=dto.pricing_tier.strip() if dto.pricing_tier else "Trung cấp",
        strengths=dto.strengths.strip() if dto.strengths else None,
        weaknesses=dto.weaknesses.strip() if dto.weaknesses else None,
        win_rate=dto.win_rate if dto.win_rate is not None else 50.0,
        is_active=dto.is_active if dto.is_active is not None else True,
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)

    return CompetitorDTO(
        id=comp.id,
        name=comp.name,
        website=comp.website,
        pricing_tier=comp.pricing_tier or "Trung cấp",
        strengths=comp.strengths,
        weaknesses=comp.weaknesses,
        win_rate=float(comp.win_rate) if comp.win_rate is not None else 50.0,
        is_active=comp.is_active,
    )


@router.put(
    "/competitors/{competitor_id}",
    response_model=CompetitorDTO,
    summary="Cập nhật đối thủ cạnh tranh",
)
def update_competitor(
    competitor_id: str,
    dto: UpdateCompetitorDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompetitorDTO:
    comp = db.query(Competitor).filter(Competitor.id == competitor_id).first()
    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đối thủ cạnh tranh cần cập nhật.",
        )

    if dto.name is not None:
        clean_name = dto.name.strip()
        conflict = (
            db.query(Competitor)
            .filter(Competitor.name == clean_name, Competitor.id != competitor_id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Đối thủ cạnh tranh '{clean_name}' đã tồn tại.",
            )
        comp.name = clean_name

    if dto.website is not None:
        comp.website = dto.website.strip() if dto.website else None

    if dto.pricing_tier is not None:
        comp.pricing_tier = dto.pricing_tier.strip() if dto.pricing_tier else "Trung cấp"

    if dto.strengths is not None:
        comp.strengths = dto.strengths.strip() if dto.strengths else None

    if dto.weaknesses is not None:
        comp.weaknesses = dto.weaknesses.strip() if dto.weaknesses else None

    if dto.win_rate is not None:
        comp.win_rate = dto.win_rate

    if dto.is_active is not None:
        comp.is_active = dto.is_active

    db.commit()
    db.refresh(comp)

    return CompetitorDTO(
        id=comp.id,
        name=comp.name,
        website=comp.website,
        pricing_tier=comp.pricing_tier or "Trung cấp",
        strengths=comp.strengths,
        weaknesses=comp.weaknesses,
        win_rate=float(comp.win_rate) if comp.win_rate is not None else 50.0,
        is_active=comp.is_active,
    )


@router.delete(
    "/competitors/{competitor_id}",
    summary="Xóa đối thủ cạnh tranh",
)
def delete_competitor(
    competitor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = db.query(Competitor).filter(Competitor.id == competitor_id).first()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đối thủ cạnh tranh cần xóa.",
        )

    deleted_name = c.name
    db.delete(c)
    db.commit()

    return {"message": f"Đã xóa đối thủ cạnh tranh '{deleted_name}' thành công."}
