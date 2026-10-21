import uuid
import secrets
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from fastapi import HTTPException, status

from app.models.quotation import Quotation, QuoteItem, QuoteApprovalHistory
from app.models.user import User
from app.models.customer import Customer
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.product import Product
from app.schemas.quotation import (
    CreateQuotationDTO,
    UpdateQuotationDTO,
    QuoteLineItemDTO,
    QuoteApprovalHistoryDTO,
    QuotationDTO,
    QuoteCompareDTO,
)
from app.repositories.quotation_repository import QuotationRepository
from app.repositories.customer_repository import CustomerRepository
from app.core.number_to_words import convert_number_to_vietnamese_words
from app.services.notification_service import NotificationService
from app.services.automation_service import AutomationService
from app.services.pdf_template_service import PdfTemplateService


DEFAULT_DISCOUNT_THRESHOLD_1 = 15.0  # Team Leader approval
DEFAULT_DISCOUNT_THRESHOLD_2 = 20.0  # Director approval


class QuotationService:
    """
    S7-01 -> S7-06: Tầng Service xử lý nghiệp vụ Quản lý Báo giá Toàn diện.
    - S7-01: Soạn thảo, tính toán chiết khấu, giá trị, điều khoản.
    - S7-02: Phê duyệt chiết khấu đa cấp, lịch sử bất biến.
    - S7-03: Quản lý phiên bản báo giá, so sánh side-by-side.
    - S7-05: Xuất PDF theo mẫu cấu hình, số tiền thành chữ.
    - S7-06: Cổng duyệt khách hàng, phản hồi tức thời & tự động hết hạn.
    """

    @staticmethod
    def calculate_pricing(
        items_dto: List[QuoteLineItemDTO],
        threshold_percent: float = DEFAULT_DISCOUNT_THRESHOLD_1,
    ) -> Dict[str, Any]:
        """Tính toán tức thời giá trị từng dòng và tổng thể báo giá."""
        subtotal = 0.0
        total_discount = 0.0
        total_vat = 0.0
        processed_items = []
        requires_approval = False
        approval_level = None
        has_below_floor = False

        for it in items_dto:
            qty = max(1, it.quantity)
            price = max(0.0, float(it.unitPrice))
            line_gross = qty * price

            # Chiết khấu theo % hoặc số tiền tuyệt đối
            if it.discountType == "amount":
                disc_amount = min(line_gross, max(0.0, float(it.discountValue)))
                disc_val = disc_amount
            else:
                disc_val = max(0.0, min(100.0, float(it.discountValue)))
                disc_amount = round((line_gross * disc_val) / 100.0, 2)

            line_net = max(0.0, line_gross - disc_amount)

            # Kiểm tra giá sàn (Floor Price)
            net_unit_price = line_net / qty if qty > 0 else price
            if it.floorPrice is not None and net_unit_price < float(it.floorPrice):
                has_below_floor = True

            vat_rate = max(0.0, min(100.0, float(it.vatRate)))
            vat_amount = round((line_net * vat_rate) / 100.0, 2)

            subtotal += line_gross
            total_discount += disc_amount
            total_vat += vat_amount

            processed_items.append({
                "productId": it.productId,
                "productCode": it.productCode,
                "productName": it.productName,
                "description": it.description,
                "quantity": qty,
                "unit": it.unit,
                "unitPrice": price,
                "discountType": it.discountType,
                "discountValue": disc_val,
                "discountAmount": disc_amount,
                "floorPrice": it.floorPrice,
                "vatRate": vat_rate,
                "vatAmount": vat_amount,
                "lineTotal": line_net,
            })

        total_discount_percent = round((total_discount / subtotal * 100.0), 2) if subtotal > 0 else 0.0
        grand_total = max(0.0, subtotal - total_discount) + total_vat

        # S7-02: Phân cấp phê duyệt
        if total_discount_percent > DEFAULT_DISCOUNT_THRESHOLD_2 or has_below_floor:
            requires_approval = True
            approval_level = "director"
        elif total_discount_percent > threshold_percent:
            requires_approval = True
            approval_level = "team_leader"

        return {
            "subtotal": round(subtotal, 2),
            "totalDiscountAmount": round(total_discount, 2),
            "totalDiscountPercent": total_discount_percent,
            "vatAmount": round(total_vat, 2),
            "grandTotal": round(grand_total, 2),
            "requiresApproval": requires_approval,
            "approvalLevel": approval_level,
            "items": processed_items,
        }

    @classmethod
    def map_to_dto(cls, q: Quotation, db: Optional[Session] = None) -> QuotationDTO:
        customer_name = q.customer.full_name if q.customer else None
        customer_company = q.customer.company if q.customer else None
        customer_email = q.customer.email if q.customer else None
        customer_phone = q.customer.phone if q.customer else None
        customer_address = q.customer.location if q.customer else None
        customer_tax_code = q.customer.tax_code if q.customer else None
        owner_name = q.owner.full_name if q.owner else None
        deal_title = q.deal.title if q.deal else None

        items_dto = [
            QuoteLineItemDTO(
                id=item.id,
                productId=item.product_id,
                productCode=item.product_code,
                productName=item.product_name,
                description=item.description,
                quantity=item.quantity,
                unit=item.unit,
                unitPrice=float(item.unit_price),
                discountType=item.discount_type,
                discountValue=float(item.discount_value),
                discountAmount=float(item.discount_amount),
                floorPrice=float(item.floor_price) if item.floor_price is not None else None,
                vatRate=float(item.vat_rate),
                vatAmount=float(item.vat_amount),
                lineTotal=float(item.line_total),
            )
            for item in (q.items or [])
        ]

        history_dto = [
            QuoteApprovalHistoryDTO(
                id=h.id,
                action=h.action,
                approvalLevel=h.approval_level,
                performedById=h.performed_by_id,
                performedByName=h.performed_by_name,
                performedByRole=h.performed_by_role,
                comment=h.comment,
                createdAt=h.created_at.isoformat() if h.created_at else "",
            )
            for h in (q.approval_history or [])
        ]

        total_words = convert_number_to_vietnamese_words(float(q.grand_total or q.total_amount or 0.0))
        share_url = f"/portal/quotes/{q.access_token}" if q.access_token else None

        return QuotationDTO(
            id=q.id,
            quoteNumber=q.quote_number,
            title=q.title,
            dealId=q.deal_id,
            dealTitle=deal_title,
            customerId=q.customer_id,
            customerName=customer_name,
            customerCompany=customer_company,
            customerEmail=customer_email,
            customerPhone=customer_phone,
            customerAddress=customer_address,
            customerTaxCode=customer_tax_code,
            ownerId=q.owner_id,
            ownerName=owner_name,
            version=q.version or 1,
            isEffective=q.is_effective if q.is_effective is not None else True,
            parentQuoteId=q.parent_quote_id,
            items=items_dto,
            subtotal=float(q.subtotal or 0.0),
            totalDiscountAmount=float(q.total_discount_amount or 0.0),
            totalDiscountPercent=float(q.total_discount_percent or 0.0),
            vatAmount=float(q.vat_amount or 0.0),
            grandTotal=float(q.grand_total or q.total_amount or 0.0),
            totalAmount=float(q.grand_total or q.total_amount or 0.0),
            totalInWords=total_words,
            discountThresholdPercent=float(q.discount_threshold_percent or 15.0),
            requiresApproval=bool(q.requires_approval),
            approvalLevel=q.approval_level,
            approvalHistory=history_dto,
            status=q.status,
            validUntil=q.valid_until.isoformat() if q.valid_until else None,
            paymentTerms=q.payment_terms,
            deliveryTerms=q.delivery_terms,
            notes=q.notes,
            accessToken=q.access_token,
            shareUrl=share_url,
            templateId=q.template_id,
            createdAt=q.created_at.isoformat() if q.created_at else None,
            updatedAt=q.updated_at.isoformat() if q.updated_at else None,
        )

    @classmethod
    def get_quotations(
        cls,
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[QuotationDTO], int]:
        cls.auto_expire_quotes(db)
        query = db.query(Quotation)
        if user is not None:
            query = QuotationRepository.apply_data_scope_filter(query, user, Quotation)

        if search and search.strip():
            pat = f"%{search.strip()}%"
            query = query.filter(Quotation.title.ilike(pat) | Quotation.quote_number.ilike(pat))

        if status and status.lower() != "all":
            query = query.filter(Quotation.status == status.lower())

        if customer_id:
            query = query.filter(Quotation.customer_id == customer_id)

        if deal_id:
            query = query.filter(Quotation.deal_id == deal_id)

        total = query.count()
        quotes = query.order_by(Quotation.created_at.desc()).offset(skip).limit(limit).all()
        return [cls.map_to_dto(q, db) for q in quotes], total

    @classmethod
    def get_quotation_by_id(
        cls,
        db: Session,
        quotation_id: str,
        user: Optional[User] = None,
    ) -> QuotationDTO:
        cls.auto_expire_quotes(db)
        if user is not None:
            q = QuotationRepository.get_scoped_by_id(db, quotation_id, user)
        else:
            q = QuotationRepository.get_by_id(db, quotation_id)

        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo giá.")
        return cls.map_to_dto(q, db)

    @classmethod
    def create_quotation(
        cls,
        db: Session,
        dto: CreateQuotationDTO,
        user: User,
    ) -> QuotationDTO:
        # 1. Xác thực khách hàng
        customer = CustomerRepository.get_scoped_by_id(db, dto.customerId, user)

        # 2. Sinh mã báo giá nếu chưa có
        quote_number = dto.quoteNumber
        if not quote_number:
            year = datetime.utcnow().year
            rand_suffix = secrets.token_hex(2).upper()
            quote_number = f"BG-{year}-{rand_suffix}"

        # 3. Kế thừa dòng sản phẩm từ Deal nếu dealId có sẵn và dto.items rỗng
        line_items_dto = dto.items
        if (not line_items_dto or len(line_items_dto) == 0) and dto.dealId:
            deal = db.query(Deal).filter(Deal.id == dto.dealId).first()
            if deal and deal.deal_items:
                line_items_dto = [
                    QuoteLineItemDTO(
                        productId=di.product_id,
                        productName=di.product_name,
                        quantity=di.quantity,
                        unit="Tháng" if di.billing_cycle == "monthly" else "Năm",
                        unitPrice=float(di.unit_price),
                        discountType="percent",
                        discountValue=float(di.discount_percent or 0.0),
                        vatRate=10.0,
                    )
                    for di in deal.deal_items
                ]

        threshold = dto.discountThresholdPercent or DEFAULT_DISCOUNT_THRESHOLD_1
        pricing = cls.calculate_pricing(line_items_dto, threshold_percent=threshold)

        valid_date = None
        if dto.validUntil:
            try:
                valid_date = datetime.strptime(dto.validUntil, "%Y-%m-%d").date()
            except Exception:
                pass

        quote_id = str(uuid.uuid4())
        access_token = secrets.token_urlsafe(32)

        # Trạng thái ban đầu
        initial_status = dto.status or "draft"
        if initial_status == "submitted" or initial_status == "pending_approval":
            initial_status = "pending_approval" if pricing["requiresApproval"] else "approved"

        quotation = Quotation(
            id=quote_id,
            quote_number=quote_number,
            title=dto.title,
            deal_id=dto.dealId,
            customer_id=customer.id,
            owner_id=user.id,
            version=1,
            is_effective=True,
            subtotal=pricing["subtotal"],
            total_discount_amount=pricing["totalDiscountAmount"],
            total_discount_percent=pricing["totalDiscountPercent"],
            vat_amount=pricing["vatAmount"],
            grand_total=pricing["grandTotal"],
            total_amount=pricing["grandTotal"],
            discount_threshold_percent=threshold,
            requires_approval=pricing["requiresApproval"],
            approval_level=pricing["approvalLevel"],
            valid_until=valid_date,
            payment_terms=dto.paymentTerms or "Thanh toán 100% trong 15 ngày kể từ ngày ký biên bản nghiệm thu.",
            delivery_terms=dto.deliveryTerms or "Bàn giao trong vòng 05 ngày làm việc kể từ ngày thanh toán đợt 1.",
            notes=dto.notes,
            status=initial_status,
            access_token=access_token,
            template_id=dto.templateId,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(quotation)
        db.flush()

        # Tạo các dòng sản phẩm
        for pi in pricing["items"]:
            item = QuoteItem(
                id=str(uuid.uuid4()),
                quote_id=quote_id,
                product_id=pi["productId"],
                product_code=pi["productCode"],
                product_name=pi["productName"],
                description=pi["description"],
                quantity=pi["quantity"],
                unit=pi["unit"],
                unit_price=pi["unitPrice"],
                discount_type=pi["discountType"],
                discount_value=pi["discountValue"],
                discount_amount=pi["discountAmount"],
                floor_price=pi["floorPrice"],
                vat_rate=pi["vatRate"],
                vat_amount=pi["vatAmount"],
                line_total=pi["lineTotal"],
            )
            db.add(item)

        # Nếu tự động duyệt -> ghi nhận lịch sử bất biến
        if not pricing["requiresApproval"] and initial_status == "approved":
            hist = QuoteApprovalHistory(
                id=str(uuid.uuid4()),
                quote_id=quote_id,
                action="auto_approved",
                approval_level="system",
                performed_by_id=user.id,
                performed_by_name="Hệ thống tự động",
                performed_by_role="Hệ thống",
                comment=f"Tự động duyệt: Mức chiết khấu ({pricing['totalDiscountPercent']}%) nằm dưới ngưỡng {threshold}%.",
                created_at=datetime.utcnow(),
            )
            db.add(hist)
        elif pricing["requiresApproval"] and initial_status == "pending_approval":
            NotificationService.notify_quote_pending_approval(
                db=db,
                quote_id=quotation.id,
                quote_number=quotation.quote_number,
                title=quotation.title,
                approval_level=pricing["approvalLevel"] or "team_leader",
                creator_name=user.full_name or user.email,
            )

        db.commit()
        db.refresh(quotation)

        # Trigger Automation Rules
        AutomationService.evaluate_and_execute(
            db=db,
            trigger_entity="quotation",
            trigger_event="created",
            entity_id=quotation.id,
            record_data={"quote_number": quotation.quote_number, "status": quotation.status, "owner_id": quotation.owner_id},
            actor_user=user,
        )

        return cls.map_to_dto(quotation, db)

    @classmethod
    def update_quotation(
        cls,
        db: Session,
        quotation_id: str,
        dto: UpdateQuotationDTO,
        user: User,
    ) -> QuotationDTO:
        """
        S7-03: Cập nhật hoặc tạo phiên bản mới nếu báo giá đã gửi (sent).
        """
        quote = QuotationRepository.get_scoped_by_id(db, quotation_id, user)
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo giá.")

        # S7-03: Nếu báo giá đã ở trạng thái 'sent' hoặc 'accepted' -> TẠO PHIÊN BẢN MỚI
        if quote.status in ("sent", "accepted", "approved"):
            return cls._create_new_version(db, quote, dto, user)

        # Ngược lại, nếu đang ở 'draft' hoặc 'rejected', cập nhật trực tiếp
        if dto.title:
            quote.title = dto.title
        if dto.validUntil:
            try:
                quote.valid_until = datetime.strptime(dto.validUntil, "%Y-%m-%d").date()
            except Exception:
                pass
        if dto.paymentTerms:
            quote.payment_terms = dto.paymentTerms
        if dto.deliveryTerms:
            quote.delivery_terms = dto.deliveryTerms
        if dto.notes is not None:
            quote.notes = dto.notes
        if dto.templateId:
            quote.template_id = dto.templateId

        if dto.items is not None:
            # Xóa các dòng cũ và tính toán lại
            db.query(QuoteItem).filter(QuoteItem.quote_id == quote.id).delete()
            threshold = float(quote.discount_threshold_percent or 15.0)
            pricing = cls.calculate_pricing(dto.items, threshold_percent=threshold)

            quote.subtotal = pricing["subtotal"]
            quote.total_discount_amount = pricing["totalDiscountAmount"]
            quote.total_discount_percent = pricing["totalDiscountPercent"]
            quote.vat_amount = pricing["vatAmount"]
            quote.grand_total = pricing["grandTotal"]
            quote.total_amount = pricing["grandTotal"]
            quote.requires_approval = pricing["requiresApproval"]
            quote.approval_level = pricing["approvalLevel"]

            for pi in pricing["items"]:
                item = QuoteItem(
                    id=str(uuid.uuid4()),
                    quote_id=quote.id,
                    product_id=pi["productId"],
                    product_code=pi["productCode"],
                    product_name=pi["productName"],
                    description=pi["description"],
                    quantity=pi["quantity"],
                    unit=pi["unit"],
                    unit_price=pi["unitPrice"],
                    discount_type=pi["discountType"],
                    discount_value=pi["discountValue"],
                    discount_amount=pi["discountAmount"],
                    floor_price=pi["floorPrice"],
                    vat_rate=pi["vatRate"],
                    vat_amount=pi["vatAmount"],
                    line_total=pi["lineTotal"],
                )
                db.add(item)

        quote.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(quote)
        return cls.map_to_dto(quote, db)

    @classmethod
    def _create_new_version(
        cls,
        db: Session,
        original_quote: Quotation,
        dto: UpdateQuotationDTO,
        user: User,
    ) -> QuotationDTO:
        """
        S7-03: Nhân bản báo giá thành phiên bản mới (Version N+1).
        Hủy hiệu lực của phiên bản cũ (is_effective = False).
        """
        # Đánh dấu phiên bản trước không còn hiệu lực chính
        original_quote.is_effective = False
        db.flush()

        new_version_num = (original_quote.version or 1) + 1
        new_quote_id = str(uuid.uuid4())
        new_access_token = secrets.token_urlsafe(32)

        # Tính toán lại dòng sản phẩm
        items_source = dto.items if dto.items is not None else [
            QuoteLineItemDTO(
                productId=i.product_id,
                productCode=i.product_code,
                productName=i.product_name,
                description=i.description,
                quantity=i.quantity,
                unit=i.unit,
                unitPrice=float(i.unit_price),
                discountType=i.discount_type,
                discountValue=float(i.discount_value),
                vatRate=float(i.vat_rate),
            )
            for i in original_quote.items
        ]

        threshold = float(original_quote.discount_threshold_percent or 15.0)
        pricing = cls.calculate_pricing(items_source, threshold_percent=threshold)

        valid_date = original_quote.valid_until
        if dto.validUntil:
            try:
                valid_date = datetime.strptime(dto.validUntil, "%Y-%m-%d").date()
            except Exception:
                pass

        new_quote = Quotation(
            id=new_quote_id,
            quote_number=f"{original_quote.quote_number}-V{new_version_num}",
            title=dto.title or f"{original_quote.title} (v{new_version_num})",
            deal_id=original_quote.deal_id,
            customer_id=original_quote.customer_id,
            owner_id=user.id,
            version=new_version_num,
            is_effective=True,
            parent_quote_id=original_quote.id,
            subtotal=pricing["subtotal"],
            total_discount_amount=pricing["totalDiscountAmount"],
            total_discount_percent=pricing["totalDiscountPercent"],
            vat_amount=pricing["vatAmount"],
            grand_total=pricing["grandTotal"],
            total_amount=pricing["grandTotal"],
            discount_threshold_percent=threshold,
            requires_approval=pricing["requiresApproval"],
            approval_level=pricing["approvalLevel"],
            valid_until=valid_date,
            payment_terms=dto.paymentTerms or original_quote.payment_terms,
            delivery_terms=dto.deliveryTerms or original_quote.delivery_terms,
            notes=dto.notes if dto.notes is not None else original_quote.notes,
            status="draft",
            access_token=new_access_token,
            template_id=dto.templateId or original_quote.template_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_quote)
        db.flush()

        for pi in pricing["items"]:
            item = QuoteItem(
                id=str(uuid.uuid4()),
                quote_id=new_quote_id,
                product_id=pi["productId"],
                product_code=pi["productCode"],
                product_name=pi["productName"],
                description=pi["description"],
                quantity=pi["quantity"],
                unit=pi["unit"],
                unit_price=pi["unitPrice"],
                discount_type=pi["discountType"],
                discount_value=pi["discountValue"],
                discount_amount=pi["discountAmount"],
                floor_price=pi["floorPrice"],
                vat_rate=pi["vatRate"],
                vat_amount=pi["vatAmount"],
                line_total=pi["lineTotal"],
            )
            db.add(item)

        # Thêm log lịch sử
        hist = QuoteApprovalHistory(
            id=str(uuid.uuid4()),
            quote_id=new_quote_id,
            action="returned_for_edit",
            approval_level="system",
            performed_by_id=user.id,
            performed_by_name=user.full_name or user.email,
            performed_by_role=user.role,
            comment=f"Khởi tạo phiên bản v{new_version_num} từ báo giá {original_quote.quote_number}.",
            created_at=datetime.utcnow(),
        )
        db.add(hist)
        db.commit()
        db.refresh(new_quote)
        return cls.map_to_dto(new_quote, db)

    @classmethod
    def submit_for_approval(cls, db: Session, quote_id: str, user: User) -> QuotationDTO:
        """
        S7-02: Đệ trình báo giá để phê duyệt hoặc tự động duyệt.
        """
        quote = QuotationRepository.get_scoped_by_id(db, quote_id, user)
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo giá.")

        if not quote.items or len(quote.items) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Báo giá phải có ít nhất 1 dòng sản phẩm.")

        if not quote.valid_until:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vui lòng thiết lập ngày hết hạn hiệu lực.")

        if quote.valid_until < date.today():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ngày hết hiệu lực không thể nằm trong quá khứ.")

        # Kiểm tra duyệt
        if quote.requires_approval:
            quote.status = "pending_approval"
            NotificationService.notify_quote_pending_approval(
                db=db,
                quote_id=quote.id,
                quote_number=quote.quote_number,
                title=quote.title,
                approval_level=quote.approval_level or "team_leader",
                creator_name=user.full_name or user.email,
            )
        else:
            quote.status = "approved"
            hist = QuoteApprovalHistory(
                id=str(uuid.uuid4()),
                quote_id=quote.id,
                action="auto_approved",
                approval_level="system",
                performed_by_id=user.id,
                performed_by_name="Hệ thống tự động",
                performed_by_role="Hệ thống",
                comment="Tự động duyệt: Mức chiết khấu nằm dưới ngưỡng phê duyệt.",
                created_at=datetime.utcnow(),
            )
            db.add(hist)

        quote.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(quote)
        return cls.map_to_dto(quote, db)

    @classmethod
    def decide_approval(
        cls,
        db: Session,
        quote_id: str,
        action: str,
        comment: Optional[str],
        user: User,
    ) -> QuotationDTO:
        """
        S7-02: Quyết định phê duyệt: Approve, Reject, Return for Revision.
        Bắt buộc nhập ý kiến (comment) khi Từ chối hoặc Trả lại chỉnh sửa.
        """
        quote = db.query(Quotation).filter(Quotation.id == quote_id).first()
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo giá.")

        if quote.status != "pending_approval":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Báo giá không ở trạng thái chờ duyệt.")

        normalized_action = action.lower()
        if normalized_action not in ("approved", "rejected", "returned_for_edit"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hành động không hợp lệ.")

        # S7-02: Bắt buộc nhận xét khi Từ chối hoặc Trả lại
        if normalized_action in ("rejected", "returned_for_edit") and (not comment or not comment.strip()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bắt buộc phải nhập ý kiến/lý do khi Từ chối hoặc Yêu cầu chỉnh sửa báo giá.",
            )

        # Kiểm tra quyền duyệt theo cấp độ
        user_role = (user.role or "").lower()
        is_director = any(r in user_role for r in ("director", "vp", "admin", "giám đốc"))
        is_leader = is_director or any(r in user_role for r in ("leader", "manager", "trưởng nhóm"))

        if quote.approval_level == "director" and not is_director:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Báo giá này yêu cầu Giám đốc Kinh doanh (Sales Director) phê duyệt.",
            )
        if quote.approval_level == "team_leader" and not is_leader:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền Trưởng nhóm để phê duyệt báo giá này.",
            )

        # Cập nhật trạng thái
        if normalized_action == "approved":
            quote.status = "approved"
        elif normalized_action == "rejected":
            quote.status = "rejected"
        elif normalized_action == "returned_for_edit":
            quote.status = "draft"

        # Ghi nhận lịch sử bất biến
        hist = QuoteApprovalHistory(
            id=str(uuid.uuid4()),
            quote_id=quote.id,
            action=normalized_action,
            approval_level=quote.approval_level,
            performed_by_id=user.id,
            performed_by_name=user.full_name or user.email,
            performed_by_role=user.role,
            comment=comment.strip() if comment else "Đã phê duyệt thành công.",
            created_at=datetime.utcnow(),
        )
        db.add(hist)
        quote.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(quote)

        # Gửi thông báo cho người lập báo giá
        NotificationService.create_notification(
            db=db,
            user_id=quote.owner_id,
            notif_type="quote_decision",
            title=f"Báo giá {quote.quote_number} đã được {hist.performed_by_name} xử lý",
            description=f"Kết quả: {normalized_action.upper()}. Ý kiến: '{comment or ''}'",
            target_type="quotation",
            target_id=quote.id,
            link_url="/deals",
        )

        AutomationService.evaluate_and_execute(
            db=db,
            trigger_entity="quotation",
            trigger_event="status_changed",
            entity_id=quote.id,
            record_data={"quote_number": quote.quote_number, "status": quote.status, "owner_id": quote.owner_id},
            actor_user=user,
        )

        return cls.map_to_dto(quote, db)

    @classmethod
    def send_quotation(cls, db: Session, quote_id: str, user: User) -> QuotationDTO:
        """
        S7-02 & S7-06: Chỉ báo giá đã được duyệt (status='approved') mới có thể gửi cho khách hàng.
        """
        quote = QuotationRepository.get_scoped_by_id(db, quote_id, user)
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo giá.")

        if quote.status != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chỉ báo giá đã được phê duyệt mới được phép gửi cho khách hàng.",
            )

        if not quote.access_token:
            quote.access_token = secrets.token_urlsafe(32)

        quote.status = "sent"
        quote.updated_at = datetime.utcnow()

        # Thêm log lịch sử
        hist = QuoteApprovalHistory(
            id=str(uuid.uuid4()),
            quote_id=quote.id,
            action="sent",
            approval_level="sales",
            performed_by_id=user.id,
            performed_by_name=user.full_name or user.email,
            performed_by_role=user.role,
            comment="Đã phát hành báo giá và gửi liên kết truy cập trực tuyến cho khách hàng.",
            created_at=datetime.utcnow(),
        )
        db.add(hist)

        # Ghi nhận hoạt động trên Deal Timeline
        if quote.deal_id:
            act = Activity(
                id=str(uuid.uuid4()),
                deal_id=quote.deal_id,
                customer_id=quote.customer_id,
                user_id=user.id,
                type="quote_sent",
                title=f"Đã phát hành Báo giá {quote.quote_number}",
                description=f"Giá trị: {float(quote.grand_total):,.0f} VNĐ. Hạn hiệu lực: {quote.valid_until}.",
                created_at=datetime.utcnow(),
            )
            db.add(act)

        db.commit()
        db.refresh(quote)
        return cls.map_to_dto(quote, db)

    @classmethod
    def compare_versions(
        cls,
        db: Session,
        quote_id_a: str,
        quote_id_b: str,
        user: User,
    ) -> QuoteCompareDTO:
        """
        S7-03: So sánh trực quan side-by-side giữa hai phiên bản của báo giá.
        """
        q_a = QuotationRepository.get_scoped_by_id(db, quote_id_a, user)
        q_b = QuotationRepository.get_scoped_by_id(db, quote_id_b, user)

        dto_a = cls.map_to_dto(q_a, db)
        dto_b = cls.map_to_dto(q_b, db)

        price_diff = dto_b.grandTotal - dto_a.grandTotal
        disc_diff = dto_b.totalDiscountPercent - dto_a.totalDiscountPercent

        items_mod = len(dto_a.items) != len(dto_b.items) or any(
            ia.productName != ib.productName or ia.quantity != ib.quantity or ia.unitPrice != ib.unitPrice
            for ia, ib in zip(dto_a.items, dto_b.items)
        )
        terms_mod = (dto_a.paymentTerms != dto_b.paymentTerms) or (dto_a.deliveryTerms != dto_b.deliveryTerms)

        summary_parts = []
        if price_diff > 0:
            summary_parts.append(f"Tổng tiền tăng {price_diff:,.0f} VNĐ")
        elif price_diff < 0:
            summary_parts.append(f"Tổng tiền giảm {abs(price_diff):,.0f} VNĐ")
        else:
            summary_parts.append("Tổng tiền giữ nguyên")

        if disc_diff != 0:
            summary_parts.append(f"Mức chiết khấu thay đổi {disc_diff:+.1f}%")

        if items_mod:
            summary_parts.append("Danh mục sản phẩm có sự thay đổi")
        if terms_mod:
            summary_parts.append("Điều khoản thương mại đã được cập nhật")

        return QuoteCompareDTO(
            versionA=dto_a,
            versionB=dto_b,
            priceDifference=round(price_diff, 2),
            discountDifference=round(disc_diff, 2),
            itemsModified=items_mod,
            termsModified=terms_mod,
            summary="; ".join(summary_parts) + ".",
        )

    @classmethod
    def get_public_quote(cls, db: Session, access_token: str) -> QuotationDTO:
        """
        S7-06: Khách hàng mở link báo giá riêng biệt (không cần đăng nhập).
        Tự động hết hạn nếu quá hạn hiệu lực.
        """
        quote = db.query(Quotation).filter(Quotation.access_token == access_token).first()
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liên kết báo giá không tồn tại hoặc đã bị thu hồi.")

        # Kiểm tra tự động hết hạn
        if quote.valid_until and quote.valid_until < date.today() and quote.status in ("sent", "draft", "pending_approval"):
            quote.status = "expired"
            quote.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(quote)

        return cls.map_to_dto(quote, db)

    @classmethod
    def respond_public_quote(
        cls,
        db: Session,
        access_token: str,
        action: str,
        comment: Optional[str] = None,
        signer_name: Optional[str] = None,
    ) -> QuotationDTO:
        """
        S7-06: Khách hàng Accept/Reject báo giá trực tuyến kèm ý kiến phản hồi.
        Cập nhật tức thời trạng thái báo giá và Timeline cơ hội bán hàng.
        """
        quote = db.query(Quotation).filter(Quotation.access_token == access_token).first()
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liên kết báo giá không tồn tại.")

        if quote.valid_until and quote.valid_until < date.today():
            quote.status = "expired"
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Báo giá này đã hết thời hạn hiệu lực.")

        if quote.status not in ("sent", "approved"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Báo giá đang ở trạng thái '{quote.status}', không thể phản hồi tiếp.",
            )

        normalized_action = action.lower()
        if normalized_action not in ("accepted", "rejected"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hành động chỉ nhận 'accepted' hoặc 'rejected'.")

        quote.status = normalized_action
        quote.updated_at = datetime.utcnow()

        actor_name = signer_name.strip() if signer_name else (quote.customer.full_name if quote.customer else "Khách hàng")

        # Ghi nhận lịch sử bất biến
        hist = QuoteApprovalHistory(
            id=str(uuid.uuid4()),
            quote_id=quote.id,
            action=normalized_action,
            approval_level="customer",
            performed_by_id=None,
            performed_by_name=actor_name,
            performed_by_role="Khách hàng",
            comment=comment.strip() if comment else ("Khách hàng đã đồng ý báo giá trực tuyến." if normalized_action == "accepted" else "Khách hàng từ chối báo giá."),
            created_at=datetime.utcnow(),
        )
        db.add(hist)

        # Cập nhật Deal Timeline ngay lập tức
        if quote.deal_id:
            act_type = "quote_accepted" if normalized_action == "accepted" else "quote_rejected"
            title_text = f"Khách hàng CHẤP NHẬN Báo giá {quote.quote_number}" if normalized_action == "accepted" else f"Khách hàng TỪ CHỐI Báo giá {quote.quote_number}"
            act = Activity(
                id=str(uuid.uuid4()),
                deal_id=quote.deal_id,
                customer_id=quote.customer_id,
                user_id=quote.owner_id,
                type=act_type,
                title=title_text,
                description=f"Người phản hồi: {actor_name}. Ý kiến: '{comment or 'Không có'}'.",
                created_at=datetime.utcnow(),
            )
            db.add(act)

        # Gửi thông báo In-App cho chuyên viên bán hàng
        NotificationService.notify_quote_customer_response(
            db=db,
            quote_id=quote.id,
            quote_number=quote.quote_number,
            owner_id=quote.owner_id,
            action=normalized_action,
            comment=comment,
        )

        db.commit()
        db.refresh(quote)

        # Trigger Automation Rules
        AutomationService.evaluate_and_execute(
            db=db,
            trigger_entity="quotation",
            trigger_event="status_changed",
            entity_id=quote.id,
            record_data={"quote_number": quote.quote_number, "status": quote.status, "owner_id": quote.owner_id},
        )

        return cls.map_to_dto(quote, db)

    @staticmethod
    def auto_expire_quotes(db: Session) -> int:
        """
        S7-06: Tự động chuyển trạng thái expired cho các báo giá đã quá ngày hiệu lực.
        """
        today = date.today()
        stale_quotes = db.query(Quotation).filter(
            Quotation.valid_until < today,
            Quotation.status.in_(("sent", "pending_approval", "draft")),
        ).all()

        count = 0
        for q in stale_quotes:
            q.status = "expired"
            q.updated_at = datetime.utcnow()
            count += 1
            if q.deal_id:
                act = Activity(
                    id=str(uuid.uuid4()),
                    deal_id=q.deal_id,
                    customer_id=q.customer_id,
                    user_id=q.owner_id,
                    type="quote_expired",
                    title=f"Báo giá {q.quote_number} đã hết hạn hiệu lực",
                    description=f"Hết hạn ngày: {q.valid_until}. Tự động chuyển sang Expired.",
                    created_at=datetime.utcnow(),
                )
                db.add(act)

        if count > 0:
            db.commit()
        return count
