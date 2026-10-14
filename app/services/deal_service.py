import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.deal import Deal
from app.models.deal_item import DealItem
from app.models.user import User
from app.models.customer import Customer
from app.models.product import Product
from app.models.pipeline_stage import PipelineStage
from app.models.audit_log import AuditLog
from app.schemas.deal import (
    CreateDealDTO,
    UpdateDealDTO,
    DealDTO,
    DealItemDTO,
    CreateDealItemDTO,
    CloseDealDTO,
    BulkReassignDealsDTO,
    SalesForecastDTO,
    ForecastPeriodSummary,
)
from app.repositories.deal_repository import DealRepository


STAGE_PROBABILITY_MAP = {
    "lead": 20,
    "contact": 40,
    "contacted": 40,
    "proposal": 60,
    "negotiation": 80,
    "won": 100,
    "lost": 0,
}


class DealService:
    """
    Tầng Service xử lý toàn bộ nghiệp vụ Quản lý Cơ hội bán hàng (EP-05: Deal Management: S5-01 -> S5-08).
    """

    @classmethod
    def map_to_dto(cls, deal: Deal) -> DealDTO:
        customer_name = deal.customer.full_name if deal.customer else None
        owner_name = deal.owner.full_name if deal.owner else None
        campaign_name = deal.campaign.name if deal.campaign else None

        items_dto = [
            DealItemDTO(
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
            for item in (deal.deal_items or [])
        ]

        return DealDTO(
            id=deal.id,
            title=deal.title,
            value=float(deal.value),
            stage=deal.stage,
            probability=deal.probability,
            customerId=deal.customer_id,
            customerName=customer_name,
            ownerId=deal.owner_id,
            ownerName=owner_name,
            campaignId=deal.campaign_id,
            campaignName=campaign_name,
            expectedCloseDate=deal.expected_close_date.isoformat() if deal.expected_close_date else None,
            closeDate=deal.close_date.isoformat() if deal.close_date else None,
            actualValue=float(deal.actual_value) if deal.actual_value is not None else None,
            lossReason=deal.loss_reason,
            lossCompetitor=deal.loss_competitor,
            isStalled=deal.is_stalled,
            lastActivityAt=deal.last_activity_at.isoformat() if deal.last_activity_at else None,
            reassignmentReason=deal.reassignment_reason,
            items=items_dto,
            createdAt=deal.created_at.isoformat() if deal.created_at else None,
        )

    @staticmethod
    def get_deals(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        stage: Optional[str] = None,
        is_stalled: Optional[bool] = None,
        campaign_id: Optional[str] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Deal]:
        """Lấy danh sách Deals thỏa mãn Data Scope của người dùng."""
        return DealRepository.get_all(
            db=db,
            user=user,
            search=search,
            stage=stage,
            is_stalled=is_stalled,
            campaign_id=campaign_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_deals_for_export(
        db: Session,
        user: User,
        search: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> List[Deal]:
        return DealRepository.get_all_for_export(
            db=db,
            user=user,
            search=search,
            stage=stage,
        )

    @staticmethod
    def get_deal_by_id(
        db: Session,
        deal_id: str,
        user: Optional[User] = None,
    ) -> Optional[Deal]:
        if user is not None:
            return DealRepository.get_scoped_by_id(db, deal_id, user)
        return DealRepository.get_by_id(db, deal_id)

    @classmethod
    def create_deal(
        cls,
        db: Session,
        dto: CreateDealDTO,
        user: User,
    ) -> Deal:
        """
        S5-01: Tạo mới cơ hội bán hàng.
        - Kiểm tra khách hàng hợp lệ trong CSDL.
        - Gán xác suất thành công từ pipeline stage nếu chưa nhập.
        - Xử lý các dòng sản phẩm (Deal Items) kèm tính toán chuẩn xác trên backend.
        """
        customer = db.query(Customer).filter(Customer.id == dto.customerId).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã khách hàng '{dto.customerId}' không tồn tại trong hệ thống.",
            )

        close_d = None
        if dto.expectedCloseDate:
            try:
                close_d = date.fromisoformat(dto.expectedCloseDate)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Định dạng ngày dự kiến đóng không hợp lệ (chuẩn YYYY-MM-DD).",
                )

        stage_key = (dto.stage or "lead").lower()
        probability = dto.probability
        if probability is None or probability == 0:
            # Tra cứu từ bảng PipelineStage hoặc STAGE_PROBABILITY_MAP
            p_stage = db.query(PipelineStage).filter(PipelineStage.stage_key == stage_key).first()
            probability = p_stage.probability if p_stage else STAGE_PROBABILITY_MAP.get(stage_key, 20)

        now = datetime.utcnow()
        new_deal = Deal(
            id=str(uuid.uuid4()),
            title=dto.title.strip(),
            value=dto.value or 0.0,
            stage=stage_key,
            probability=probability,
            customer_id=customer.id,
            owner_id=user.id,
            expected_close_date=close_d,
            campaign_id=dto.campaignId,
            is_stalled=False,
            last_activity_at=now,
            created_at=now,
            updated_at=now,
        )
        saved = DealRepository.create(db, new_deal)

        # Thêm các sản phẩm nếu có
        if dto.items:
            for it in dto.items:
                cls.add_deal_item(db, saved.id, it, user)

        return saved

    @classmethod
    def update_deal(
        cls,
        db: Session,
        deal_id: str,
        dto: UpdateDealDTO,
        user: User,
    ) -> Deal:
        deal = cls.get_deal_by_id(db, deal_id, user)
        if not deal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy deal.")

        if dto.title:
            deal.title = dto.title.strip()
        if dto.value is not None:
            deal.value = dto.value
        if dto.stage:
            deal.stage = dto.stage.lower()
        if dto.probability is not None:
            deal.probability = dto.probability
        if dto.customerId:
            deal.customer_id = dto.customerId
        if dto.expectedCloseDate:
            deal.expected_close_date = date.fromisoformat(dto.expectedCloseDate)
        if dto.campaignId is not None:
            deal.campaign_id = dto.campaignId

        return DealRepository.update(db, deal)

    # =========================================================================
    # S5-03: PRODUCTS AND DEAL ITEMS
    # =========================================================================

    @classmethod
    def add_deal_item(
        cls,
        db: Session,
        deal_id: str,
        dto: CreateDealItemDTO,
        user: User,
    ) -> DealItem:
        deal = cls.get_deal_by_id(db, deal_id, user)
        if not deal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy deal.")

        product = None
        unit_price = dto.unitPrice
        product_name = dto.productName or "Sản phẩm tùy chỉnh"

        if dto.productId:
            product = db.query(Product).filter(Product.id == dto.productId).first()
            if product:
                product_name = product.name
                if unit_price is None or unit_price <= 0:
                    unit_price = float(product.selling_price)

        if unit_price is None:
            unit_price = 0.0

        quantity = max(1, dto.quantity)
        discount = max(0.0, min(100.0, float(dto.discountPercent or 0.0)))
        subtotal = quantity * unit_price * (1.0 - discount / 100.0)

        item = DealItem(
            id=str(uuid.uuid4()),
            deal_id=deal.id,
            product_id=product.id if product else None,
            product_name=product_name,
            quantity=quantity,
            unit_price=unit_price,
            discount_percent=discount,
            billing_cycle=dto.billingCycle or "annual",
            subtotal=subtotal,
            created_at=datetime.utcnow(),
        )
        saved_item = DealRepository.add_item(db, item)
        DealRepository.recalculate_deal_value(db, deal.id)
        return saved_item

    @classmethod
    def remove_deal_item(
        cls,
        db: Session,
        deal_id: str,
        item_id: str,
        user: User,
    ) -> float:
        deal = cls.get_deal_by_id(db, deal_id, user)
        if not deal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy deal.")

        success = DealRepository.delete_item(db, item_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy dòng sản phẩm.")

        new_val = DealRepository.recalculate_deal_value(db, deal.id)
        return new_val

    # =========================================================================
    # S5-04: STAGE EXIT CONDITIONS VALIDATION
    # =========================================================================

    @classmethod
    def validate_stage_exit_conditions(
        cls,
        deal: Deal,
        new_stage: str,
        override: bool = False,
        user: Optional[User] = None,
    ) -> None:
        """
        S5-04: Kiểm tra danh sách điều kiện thoát giai đoạn (Stage Requirements).
        Ngăn chuyển giai đoạn nếu chưa thỏa mãn, trừ khi Team Leader / Admin ghi đè (override=True).
        """
        current_stage = deal.stage.lower()
        target_stage = new_stage.lower()

        if current_stage == target_stage:
            return

        if override:
            # Kiểm tra quyền được ghi đè: Team Leader, Sales Manager, VP of Sales, Super Admin
            user_role = (user.role if user else "").lower()
            allowed_roles = {"admin", "super admin", "sales manager", "vp of sales", "director", "team leader"}
            if not any(r in user_role for r in allowed_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Chỉ Trưởng nhóm (Team Leader) hoặc Quản trị viên mới có quyền ghi đè điều kiện phễu.",
                )
            return

        missing_requirements = []

        # Điều kiện chuyển sang "contact" hoặc "contacted"
        if target_stage in ("contact", "contacted"):
            if not deal.customer_id:
                missing_requirements.append("Phải liên kết khách hàng doanh nghiệp hợp lệ.")

        # Điều kiện chuyển sang "proposal" (Báo giá)
        elif target_stage == "proposal":
            if float(deal.value or 0.0) <= 0:
                missing_requirements.append("Phải thiết lập giá trị cơ hội hoặc thêm ít nhất một sản phẩm/dịch vụ.")
            if not deal.expected_close_date:
                # Tự động gán 30 ngày nếu chưa có thay vì chặn cứng người dùng
                deal.expected_close_date = date.today() + timedelta(days=30)

        # Điều kiện chuyển sang "negotiation" (Thương thảo)
        elif target_stage == "negotiation":
            if float(deal.value or 0.0) <= 0:
                missing_requirements.append("Giá trị thương thảo phải lớn hơn 0.")
            if not deal.expected_close_date:
                deal.expected_close_date = date.today() + timedelta(days=30)

        # Điều kiện chuyển sang "won"
        elif target_stage == "won":
            if float(deal.value or 0.0) <= 0:
                missing_requirements.append("Giá trị thực tế ký hợp đồng phải lớn hơn 0.")

        # Điều kiện chuyển sang "lost"
        elif target_stage == "lost":
            if not deal.loss_reason:
                missing_requirements.append("Phải nhập lý do thất bại (Loss Reason).")

        if missing_requirements:
            msg = "Điều kiện thoát giai đoạn (Exit Conditions) chưa đáp ứng: " + " | ".join(missing_requirements)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            )

    @classmethod
    def move_stage(
        cls,
        db: Session,
        deal_id: str,
        new_stage: str,
        user: Optional[User] = None,
        override: bool = False,
    ) -> Deal:
        deal = cls.get_deal_by_id(db, deal_id, user)
        if not deal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy deal.")

        # Kiểm tra Stage Exit Conditions
        cls.validate_stage_exit_conditions(deal, new_stage, override=override, user=user)

        target_stage = new_stage.lower()
        deal.stage = target_stage
        deal.probability = STAGE_PROBABILITY_MAP.get(target_stage, deal.probability)
        if target_stage == "won":
            deal.close_date = date.today()
            deal.actual_value = deal.value

        updated_deal = DealRepository.update_stage(db, deal, target_stage)
        return updated_deal

    # =========================================================================
    # S5-05: CLOSE WON / CLOSE LOST
    # =========================================================================

    @classmethod
    def close_deal(
        cls,
        db: Session,
        deal_id: str,
        dto: CloseDealDTO,
        user: User,
    ) -> DealDTO:
        deal = cls.get_deal_by_id(db, deal_id, user)
        if not deal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy deal.")

        close_type = dto.stage.lower()
        now = datetime.utcnow()

        if close_type == "won":
            deal.stage = "won"
            deal.probability = 100
            deal.actual_value = dto.actualValue if dto.actualValue is not None else deal.value
            deal.close_date = date.fromisoformat(dto.signingDate) if dto.signingDate else date.today()
            audit_action = "DEAL_CLOSE_WON"
            details = f"Chốt thành công cơ hội '{deal.title}' với giá trị {deal.actual_value} VNĐ"
        elif close_type == "lost":
            if not dto.lossReason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Vui lòng cung cấp lý do thất bại khi đóng Deal Lost.",
                )
            deal.stage = "lost"
            deal.probability = 0
            deal.loss_reason = dto.lossReason
            deal.loss_competitor = dto.lossCompetitor
            deal.close_date = date.today()
            audit_action = "DEAL_CLOSE_LOST"
            details = f"Đóng thất bại cơ hội '{deal.title}'. Lý do: {dto.lossReason}, Đối thủ: {dto.lossCompetitor or 'Không có'}"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trạng thái đóng deal chỉ chấp nhận 'won' hoặc 'lost'.",
            )

        saved = DealRepository.update(db, deal)

        # Ghi nhật ký kiểm toán
        audit = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user.id,
            action=audit_action,
            performed_by=user.full_name,
            user_name=user.full_name,
            user_email=user.email,
            target_type="DEAL",
            target_id=deal.id,
            details=details,
            created_at=now,
        )
        db.add(audit)
        db.commit()

        return cls.map_to_dto(saved)

    # =========================================================================
    # S5-06: SALES FORECAST DASHBOARD
    # =========================================================================

    @classmethod
    def get_sales_forecast(cls, db: Session, user: Optional[User] = None) -> SalesForecastDTO:
        """
        S5-06: Dự báo doanh thu bán hàng theo công thức chuẩn:
        Weighted forecast = Sum(deal amount * stage win probability).
        Loại trừ các deal đã thất bại (lost) hoặc không hợp lệ.
        """
        all_deals = DealRepository.get_all(db, user=user)
        active_deals = [d for d in all_deals if d.stage != "lost"]

        total_pipeline = sum(float(d.value or 0.0) for d in active_deals)
        total_weighted = sum(float(d.value or 0.0) * (d.probability or 0) / 100.0 for d in active_deals)

        # Phân tích theo từng giai đoạn
        stage_map: Dict[str, Dict[str, Any]] = {}
        for d in all_deals:
            st = d.stage
            if st not in stage_map:
                stage_map[st] = {"stage": st, "count": 0, "totalValue": 0.0, "weightedValue": 0.0}
            stage_map[st]["count"] += 1
            stage_map[st]["totalValue"] += float(d.value or 0.0)
            stage_map[st]["weightedValue"] += float(d.value or 0.0) * (d.probability or 0) / 100.0

        # Phân tích theo kỳ (Tháng 1 -> Tháng 12)
        periods_map: Dict[str, Dict[str, Any]] = {}
        for d in active_deals:
            if d.expected_close_date:
                period_key = d.expected_close_date.strftime("Tháng %m/%Y")
            else:
                period_key = "Chưa xác định"

            if period_key not in periods_map:
                periods_map[period_key] = {"period": period_key, "count": 0, "total": 0.0, "weighted": 0.0}
            periods_map[period_key]["count"] += 1
            periods_map[period_key]["total"] += float(d.value or 0.0)
            periods_map[period_key]["weighted"] += float(d.value or 0.0) * (d.probability or 0) / 100.0

        periods = [
            ForecastPeriodSummary(
                period=v["period"],
                dealCount=v["count"],
                totalValue=round(v["total"], 2),
                weightedValue=round(v["weighted"], 2),
            )
            for v in periods_map.values()
        ]

        return SalesForecastDTO(
            totalPipelineValue=round(total_pipeline, 2),
            totalWeightedForecast=round(total_weighted, 2),
            activeDealsCount=len(active_deals),
            periods=periods,
            stageBreakdowns=list(stage_map.values()),
        )

    # =========================================================================
    # S5-07: STALLED DEALS DETECTION
    # =========================================================================

    @classmethod
    def detect_and_get_stalled_deals(
        cls,
        db: Session,
        days_threshold: int = 14,
        user: Optional[User] = None,
    ) -> List[DealDTO]:
        """
        S5-07: Nhận diện cơ hội ứ đọng (Stalled Deals):
        - Không có tương tác trong hơn `days_threshold` ngày (mặc định 14 ngày), HOẶC
        - Quá hạn ngày dự kiến đóng mà chưa thắng/thua.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
        today = date.today()

        deals = DealRepository.get_all(db, user=user)
        stalled_deals = []

        for d in deals:
            if d.stage in ("won", "lost"):
                continue

            is_inactive = d.last_activity_at and d.last_activity_at < cutoff_date
            is_overdue = d.expected_close_date and d.expected_close_date < today

            if is_inactive or is_overdue:
                d.is_stalled = True
                stalled_deals.append(d)
            else:
                d.is_stalled = False

        db.commit()
        return [cls.map_to_dto(d) for d in stalled_deals]

    @classmethod
    def scan_stalled_deals(
        cls,
        db: Session,
        days_threshold: int = 14,
        user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """
        S5-07: Quét và cập nhật cờ ứ đọng (is_stalled) cho tất cả các deal chưa đóng.
        Trả về kết quả quét tương thích với giao diện Quét Deal Ứ đọng của Frontend.
        """
        stalled_dtos = cls.detect_and_get_stalled_deals(db=db, days_threshold=days_threshold, user=user)
        deals = DealRepository.get_all(db, user=user)
        active_count = len([d for d in deals if d.stage not in ("won", "lost")])
        return {
            "message": f"Quét cơ hội ứ đọng hoàn tất. Phát hiện {len(stalled_dtos)} Deal bị ứ đọng.",
            "scannedCount": active_count,
            "newlyStalled": len(stalled_dtos),
            "stalledDeals": stalled_dtos,
        }

    # =========================================================================
    # S5-08: DEAL REASSIGNMENT
    # =========================================================================

    @classmethod
    def bulk_reassign_deals(
        cls,
        db: Session,
        dto: BulkReassignDealsDTO,
        actor: User,
    ) -> Dict[str, Any]:
        """
        S5-08: Chuyển giao hàng loạt cơ hội bán hàng cho người phụ trách mới:
        - Bắt buộc cung cấp lý do chuyển giao.
        - Ghi nhật ký đầy đủ: người cũ, người mới, lý do, người thao tác.
        """
        new_owner = db.query(User).filter(User.id == dto.newOwnerId, User.status == "active").first()
        if not new_owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Người phụ trách mới với mã ID '{dto.newOwnerId}' không tồn tại hoặc đã bị khóa.",
            )

        updated_count = 0
        now = datetime.utcnow()

        for deal_id in dto.dealIds:
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if not deal:
                continue

            old_owner_id = deal.owner_id
            deal.reassigned_from_id = old_owner_id
            deal.owner_id = new_owner.id
            deal.reassignment_reason = dto.reason.strip()
            deal.updated_at = now
            deal.last_activity_at = now
            updated_count += 1

            # Ghi nhật ký kiểm toán
            audit = AuditLog(
                id=str(uuid.uuid4()),
                user_id=actor.id,
                action="DEAL_REASSIGNED",
                performed_by=actor.full_name,
                user_name=actor.full_name,
                user_email=actor.email,
                target_type="DEAL",
                target_id=deal.id,
                details=f"Chuyển cơ hội '{deal.title}' từ '{old_owner_id}' sang '{new_owner.full_name}'. Lý do: {dto.reason}",
                created_at=now,
            )
            db.add(audit)

        db.commit()

        return {
            "message": f"Chuyển giao thành công {updated_count} cơ hội bán hàng cho '{new_owner.full_name}'.",
            "updatedCount": updated_count,
            "reassignedCount": updated_count,
            "newOwnerId": new_owner.id,
            "newOwnerName": new_owner.full_name,
        }
