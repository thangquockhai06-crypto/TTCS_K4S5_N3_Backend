import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.contract import Contract, ContractItem
from app.models.quotation import Quotation
from app.models.deal import Deal
from app.models.deal_item import DealItem
from app.models.customer import Customer
from app.models.activity import Activity
from app.models.user import User
from app.schemas.contract import CreateContractDTO, ContractDTO, ContractItemDTO, ContractRenewalDTO
from app.repositories.base_repository import BaseRepository
from app.core.number_to_words import convert_number_to_vietnamese_words
from app.services.notification_service import NotificationService
from app.services.automation_service import AutomationService


DEFAULT_EXPIRY_ALERT_DAYS = 30


class ContractService:
    """
    S7-04 & S7-07: Dịch vụ Quản lý Hợp đồng & Cảnh báo Hết hạn, Tái ký.
    - S7-04: Chuyển đổi Báo giá được chấp thuận sang Hợp đồng, kế thừa sản phẩm, tự động đóng Won cho Deal.
    - S7-07: Quản lý danh sách hợp đồng, tính số ngày còn lại, cảnh báo hết hạn và tạo cơ hội tái ký.
    """

    @classmethod
    def map_to_dto(cls, c: Contract) -> ContractDTO:
        today = date.today()
        rem_days = (c.expiry_date - today).days if c.expiry_date else 0
        is_expiring_soon = 0 <= rem_days <= DEFAULT_EXPIRY_ALERT_DAYS and c.status == "active"
        is_expired = rem_days < 0 and c.status != "renewed"

        total_words = convert_number_to_vietnamese_words(float(c.total_value or 0.0))

        items_dto = [
            ContractItemDTO(
                id=item.id,
                productId=item.product_id,
                productName=item.product_name,
                quantity=item.quantity,
                unit=item.unit,
                unitPrice=float(item.unit_price),
                discountAmount=float(item.discount_amount),
                lineTotal=float(item.line_total),
            )
            for item in (c.items or [])
        ]

        return ContractDTO(
            id=c.id,
            contractNumber=c.contract_number,
            title=c.title,
            quotationId=c.quotation_id,
            dealId=c.deal_id,
            dealTitle=c.deal.title if c.deal else None,
            customerId=c.customer_id,
            customerName=c.customer.full_name if c.customer else None,
            customerCompany=c.customer.company if c.customer else None,
            customerTaxCode=c.customer.tax_code if c.customer else None,
            ownerId=c.owner_id,
            ownerName=c.owner.full_name if c.owner else None,
            totalValue=float(c.total_value or 0.0),
            totalInWords=total_words,
            signingDate=c.signing_date.isoformat() if c.signing_date else "",
            effectiveDate=c.effective_date.isoformat() if c.effective_date else "",
            expiryDate=c.expiry_date.isoformat() if c.expiry_date else "",
            remainingDays=rem_days,
            isExpiringSoon=is_expiring_soon,
            isExpired=is_expired,
            paymentTerms=c.payment_terms,
            deliveryTerms=c.delivery_terms,
            status=c.status,
            templateId=c.template_id,
            items=items_dto,
            createdAt=c.created_at.isoformat() if c.created_at else None,
            updatedAt=c.updated_at.isoformat() if c.updated_at else None,
        )

    @classmethod
    def get_contracts(
        cls,
        db: Session,
        user: User,
        search: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        expiring_within_days: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ContractDTO], int]:
        """
        S7-07: Lấy danh sách hợp đồng kèm số ngày còn lại và cảnh báo hết hạn.
        """
        query = db.query(Contract)
        query = BaseRepository.apply_data_scope_filter(query, user, Contract)

        if search and search.strip():
            pat = f"%{search.strip()}%"
            query = query.filter(Contract.contract_number.ilike(pat) | Contract.title.ilike(pat))

        if status and status.lower() != "all":
            query = query.filter(Contract.status == status.lower())

        if customer_id:
            query = query.filter(Contract.customer_id == customer_id)

        today = date.today()
        if expiring_within_days is not None:
            cutoff = today + timedelta(days=expiring_within_days)
            query = query.filter(Contract.expiry_date >= today, Contract.expiry_date <= cutoff)

        total = query.count()
        contracts = query.order_by(Contract.expiry_date.asc()).offset(skip).limit(limit).all()
        return [cls.map_to_dto(c) for c in contracts], total

    @classmethod
    def get_contract_by_id(cls, db: Session, contract_id: str, user: User) -> ContractDTO:
        contract = BaseRepository.get_scoped_record_or_raise(
            db=db,
            model=Contract,
            record_id=contract_id,
            user=user,
            not_found_msg="Không tìm thấy hợp đồng.",
            forbidden_msg="Bạn không có quyền truy cập hợp đồng này.",
        )
        return cls.map_to_dto(contract)

    @classmethod
    def convert_quotation_to_contract(
        cls,
        db: Session,
        dto: CreateContractDTO,
        user: User,
    ) -> ContractDTO:
        """
        S7-04: Chuyển đổi Báo giá thành Hợp đồng.
        - Không phải nhập lại dòng sản phẩm hay đơn giá.
        - Kiểm tra tính duy nhất của số hợp đồng (Unique Constraint).
        - Tự động chuyển Cơ hội bán hàng (Deal) sang Won với giá trị hợp đồng chính xác.
        """
        # 1. Kiểm tra báo giá
        quote = db.query(Quotation).filter(Quotation.id == dto.quotationId).first()
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo giá nguồn.")

        # Phải là báo giá hợp lệ (đã được chấp thuận hoặc đã duyệt)
        if quote.status not in ("accepted", "approved", "sent"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Báo giá đang ở trạng thái '{quote.status}'. Chỉ báo giá đã được duyệt hoặc khách hàng chấp nhận mới có thể lập hợp đồng.",
            )

        # 2. Kiểm tra tính duy nhất của số hợp đồng
        existing_contract = db.query(Contract).filter(Contract.contract_number == dto.contractNumber.strip()).first()
        if existing_contract:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số hợp đồng '{dto.contractNumber}' đã tồn tại trong hệ thống. Vui lòng nhập số hợp đồng khác.",
            )

        # 3. Phân tích các mốc ngày
        try:
            sign_d = datetime.strptime(dto.signingDate, "%Y-%m-%d").date()
            eff_d = datetime.strptime(dto.effectiveDate, "%Y-%m-%d").date()
            exp_d = datetime.strptime(dto.expiryDate, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Định dạng ngày không hợp lệ (yêu cầu YYYY-MM-DD).")

        if exp_d <= eff_d:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ngày hết hạn phải sau ngày bắt đầu có hiệu lực.")

        contract_id = str(uuid.uuid4())
        contract_title = dto.title or f"Hợp đồng kinh tế {dto.contractNumber} - {quote.title}"
        total_val = float(quote.grand_total or quote.total_amount or 0.0)

        contract = Contract(
            id=contract_id,
            contract_number=dto.contractNumber.strip(),
            title=contract_title,
            quotation_id=quote.id,
            deal_id=quote.deal_id,
            customer_id=quote.customer_id,
            owner_id=user.id,
            total_value=total_val,
            signing_date=sign_d,
            effective_date=eff_d,
            expiry_date=exp_d,
            payment_terms=dto.paymentTerms or quote.payment_terms,
            delivery_terms=dto.deliveryTerms or quote.delivery_terms,
            status="active",
            template_id=dto.templateId or quote.template_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(contract)
        db.flush()

        # 4. Kế thừa toàn bộ dòng sản phẩm từ Báo giá sang Hợp đồng (không cần nhập lại)
        for qi in (quote.items or []):
            ci = ContractItem(
                id=str(uuid.uuid4()),
                contract_id=contract_id,
                product_id=qi.product_id,
                product_name=qi.product_name,
                quantity=qi.quantity,
                unit=qi.unit,
                unit_price=qi.unit_price,
                discount_amount=qi.discount_amount,
                line_total=qi.line_total,
            )
            db.add(ci)

        # 5. S7-04: Tự động đánh dấu Cơ hội (Deal) liên kết là Won với giá trị hợp đồng chính xác
        if quote.deal_id:
            deal = db.query(Deal).filter(Deal.id == quote.deal_id).first()
            if deal:
                deal.stage = "won"
                deal.actual_value = total_val
                deal.value = total_val
                deal.probability = 100
                deal.close_date = sign_d
                deal.updated_at = datetime.utcnow()
                deal.last_activity_at = datetime.utcnow()

                # Ghi nhận hoạt động trên Deal
                act = Activity(
                    id=str(uuid.uuid4()),
                    deal_id=deal.id,
                    customer_id=deal.customer_id,
                    user_id=user.id,
                    type="contract_signed",
                    title=f"Ký kết Hợp đồng {contract.contract_number} (Deal Won)",
                    description=f"Hợp đồng kinh tế trị giá {total_val:,.0f} VNĐ đã được xác lập thành công từ Báo giá {quote.quote_number}.",
                    created_at=datetime.utcnow(),
                )
                db.add(act)

        # Cập nhật tổng giá trị hợp đồng lũy kế cho Khách hàng
        customer = db.query(Customer).filter(Customer.id == quote.customer_id).first()
        if customer:
            curr_val = float(customer.total_contract_value or 0.0)
            customer.total_contract_value = curr_val + total_val

        db.commit()
        db.refresh(contract)

        # Trigger Automation Rules
        AutomationService.evaluate_and_execute(
            db=db,
            trigger_entity="deal",
            trigger_event="status_changed",
            entity_id=quote.deal_id or contract.id,
            record_data={"stage": "won", "title": contract.title, "owner_id": user.id},
            actor_user=user,
        )

        return cls.map_to_dto(contract)

    @classmethod
    def create_renewal_opportunity(
        cls,
        db: Session,
        contract_id: str,
        dto: ContractRenewalDTO,
        user: User,
    ) -> Deal:
        """
        S7-07: Tạo cơ hội tái ký hợp đồng (Renewal Opportunity) từ hợp đồng sắp hết hạn.
        - Kế thừa khách hàng, sản phẩm và giá trị từ hợp đồng cũ.
        - Cập nhật trạng thái hợp đồng sang 'renewed'.
        """
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hợp đồng.")

        new_deal_id = str(uuid.uuid4())
        renewal_title = dto.title or f"Tái ký Hợp đồng {contract.contract_number} ({contract.customer.company if contract.customer else 'Khách hàng'})"

        close_d = None
        if dto.expectedCloseDate:
            try:
                close_d = datetime.strptime(dto.expectedCloseDate, "%Y-%m-%d").date()
            except Exception:
                pass
        if not close_d:
            close_d = contract.expiry_date or (date.today() + timedelta(days=60))

        # Tạo Deal mới cho chu kỳ tái ký
        new_deal = Deal(
            id=new_deal_id,
            title=renewal_title,
            value=contract.total_value,
            stage="proposal",
            probability=70,
            customer_id=contract.customer_id,
            owner_id=user.id,
            expected_close_date=close_d,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
        )
        db.add(new_deal)
        db.flush()

        # Kế thừa sản phẩm từ hợp đồng sang deal mới
        for ci in contract.items:
            di = DealItem(
                id=str(uuid.uuid4()),
                deal_id=new_deal_id,
                product_id=ci.product_id,
                product_name=ci.product_name,
                quantity=ci.quantity,
                unit_price=ci.unit_price,
                discount_percent=0.0,
                billing_cycle="annual",
                subtotal=ci.line_total,
                created_at=datetime.utcnow(),
            )
            db.add(di)

        # Cập nhật trạng thái hợp đồng
        contract.status = "renewed"
        contract.updated_at = datetime.utcnow()

        # Ghi nhận hoạt động trên dòng thời gian
        act = Activity(
            id=str(uuid.uuid4()),
            deal_id=new_deal_id,
            customer_id=contract.customer_id,
            user_id=user.id,
            type="contract_renewal_created",
            title=f"Khởi tạo cơ hội tái ký từ Hợp đồng {contract.contract_number}",
            description=f"Giá trị hợp đồng gốc: {float(contract.total_value):,.0f} VNĐ. Hạn cũ: {contract.expiry_date}.",
            created_at=datetime.utcnow(),
        )
        db.add(act)

        # Gửi thông báo
        NotificationService.create_notification(
            db=db,
            user_id=user.id,
            notif_type="task_assigned",
            title="Đã khởi tạo cơ hội tái ký thành công",
            description=f"Cơ hội '{renewal_title}' đã được mở. Vui lòng chuẩn bị phương án chăm sóc và báo giá gia hạn.",
            target_type="deal",
            target_id=new_deal_id,
            link_url="/deals",
        )

        db.commit()
        db.refresh(new_deal)
        return new_deal
