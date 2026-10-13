"""
LeadDuplicateService: Xử lý nghiệp vụ Phát hiện & Gộp Lead trùng lặp (SCRUM-175 / SCRUM-46 / Sprint 4).
Hỗ trợ:
- Phát hiện trùng lặp đa tiêu chí: Email, Số điện thoại (VN), Tên công ty (loại bỏ tiền tố/hậu tố doanh nghiệp).
- So sánh đối chiếu Lead với Lead và Lead với Khách hàng (Customers).
- Gợi ý gắn Lead vào Khách hàng hiện hữu (Lead-to-Customer).
- Thực thi gộp 2 Lead trùng lặp (Lead-to-Lead) bảo toàn trọn vẹn lịch sử tương tác trong Database Transaction an toàn.
"""
import re
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.lead import Lead
from app.models.customer import Customer
from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.lead_duplicate import (
    LeadDuplicateCheckRequest,
    DuplicateMatchItem,
    LeadDuplicateCheckResponse,
    LeadMergeRequest,
    LeadAttachToCustomerRequest,
)


class LeadDuplicateService:
    @staticmethod
    def normalize_phone(phone: Optional[str]) -> str:
        """Chuẩn hóa số điện thoại: loại bỏ ký tự phân cách, chuẩn hóa đầu số VN sang 0."""
        if not phone:
            return ""
        cleaned = re.sub(r"[^0-9]", "", str(phone).strip())
        if cleaned.startswith("84") and len(cleaned) == 11:
            cleaned = "0" + cleaned[2:]
        return cleaned

    @staticmethod
    def normalize_email(email: Optional[str]) -> str:
        """Chuẩn hóa email: chuyển về chữ thường và loại bỏ khoảng trắng thừa."""
        if not email:
            return ""
        return str(email).strip().lower()

    @staticmethod
    def normalize_company(company: Optional[str]) -> str:
        """
        Chuẩn hóa tên công ty:
        - Chuyển về chữ thường.
        - Loại bỏ các tiền tố / hậu tố pháp nhân phổ biến (Công ty, Cty, TNHH, CP, JSC, Corp...).
        - Loại bỏ ký tự đặc biệt, gộp khoảng trắng thừa.
        """
        if not company:
            return ""
        raw = str(company).lower()
        # Loại bỏ các tiền tố / hậu tố doanh nghiệp phổ biến
        pattern = r"\b(công ty|cty|tnhh|jsc|corp|corporation|cổ phần|cp|co\.,?\s*ltd|co\s*ltd|ltd|vietnam|việt nam|doanh nghiệp|tập đoàn)\b"
        cleaned = re.sub(pattern, "", raw, flags=re.IGNORECASE)
        # Loại bỏ ký tự đặc biệt, chỉ giữ lại chữ cái và chữ số
        cleaned = re.sub(r"[^\w\s]", "", cleaned)
        cleaned = " ".join(cleaned.split()).strip()
        return cleaned

    @classmethod
    def is_company_match(cls, comp_a: str, comp_b: str) -> bool:
        """Đối soát so khớp tên công ty (khớp chính xác hoặc tương đồng chuỗi)."""
        if not comp_a or not comp_b:
            return False
        if comp_a == comp_b:
            return True
        # Đối soát chuỗi con nếu độ dài tối thiểu 4 ký tự
        if len(comp_a) >= 4 and len(comp_b) >= 4:
            if comp_a in comp_b or comp_b in comp_a:
                return True
        return False

    @classmethod
    def check_duplicates(
        cls,
        db: Session,
        request: LeadDuplicateCheckRequest,
        current_user: User,
    ) -> LeadDuplicateCheckResponse:
        """
        Quét và phát hiện trùng lặp đa tiêu chí:
        - So khớp đối chiếu trên cả 2 nguồn: Bảng Khách hàng (Customers) và Bảng Lead (Leads).
        - Trả về danh sách trùng lặp cùng gợi ý hành động.
        """
        norm_email = cls.normalize_email(request.email)
        norm_phone = cls.normalize_phone(request.phone)
        norm_company = cls.normalize_company(request.company)

        # Nếu không có thông tin đầu vào nào để so khớp
        if not norm_email and not norm_phone and not norm_company:
            return LeadDuplicateCheckResponse(
                is_duplicate=False,
                matches_count=0,
                lead_matches=[],
                customer_matches=[],
                recommendation="NO_DUPLICATE",
                suggested_action=None,
            )

        # 1. Quét đối chiếu với bảng Khách hàng hiện có (Customers)
        customers = db.query(Customer).filter(Customer.is_deleted == False).all()
        customer_matches: List[DuplicateMatchItem] = []

        for cust in customers:
            match_fields: List[str] = []
            c_phone = cls.normalize_phone(cust.phone)
            c_email = cls.normalize_email(cust.email)
            c_comp = cls.normalize_company(cust.company)

            if norm_phone and c_phone and norm_phone == c_phone:
                match_fields.append("phone")
            if norm_email and c_email and norm_email == c_email:
                match_fields.append("email")
            if norm_company and c_comp and cls.is_company_match(norm_company, c_comp):
                match_fields.append("company")

            if match_fields:
                owner = cust.assigned_user.full_name if cust.assigned_user else None
                customer_matches.append(
                    DuplicateMatchItem(
                        target_type="CUSTOMER",
                        target_id=cust.id,
                        name=cust.company or cust.full_name,
                        email=cust.email,
                        phone=cust.phone,
                        company=cust.company,
                        owner_name=owner,
                        match_fields=match_fields,
                        created_at=cust.created_at,
                    )
                )

        # 2. Quét đối chiếu với bảng Leads (chưa bị gộp)
        lead_query = db.query(Lead).filter(Lead.status != "MERGED")
        if request.exclude_lead_id:
            lead_query = lead_query.filter(Lead.id != request.exclude_lead_id)
        leads = lead_query.all()
        lead_matches: List[DuplicateMatchItem] = []

        for l in leads:
            match_fields: List[str] = []
            l_phone = cls.normalize_phone(l.phone)
            l_email = cls.normalize_email(l.email)
            l_comp = cls.normalize_company(l.company)

            if norm_phone and l_phone and norm_phone == l_phone:
                match_fields.append("phone")
            if norm_email and l_email and norm_email == l_email:
                match_fields.append("email")
            if norm_company and l_comp and cls.is_company_match(norm_company, l_comp):
                match_fields.append("company")

            if match_fields:
                creator = l.creator.full_name if l.creator else None
                lead_matches.append(
                    DuplicateMatchItem(
                        target_type="LEAD",
                        target_id=l.id,
                        name=l.full_name,
                        email=l.email,
                        phone=l.phone,
                        company=l.company,
                        owner_name=creator,
                        match_fields=match_fields,
                        created_at=l.created_at,
                    )
                )

        # 3. Phân định gợi ý hành động (Recommendation)
        if customer_matches:
            recommendation = "ATTACH_TO_CUSTOMER"
            suggested_action = "MERGE_TO_EXISTING_CUSTOMER"
        elif lead_matches:
            recommendation = "MERGE_LEADS"
            suggested_action = "MERGE_DUPLICATE_LEADS"
        else:
            recommendation = "NO_DUPLICATE"
            suggested_action = None

        is_duplicate = bool(customer_matches or lead_matches)
        total_count = len(customer_matches) + len(lead_matches)

        return LeadDuplicateCheckResponse(
            is_duplicate=is_duplicate,
            matches_count=total_count,
            lead_matches=lead_matches,
            customer_matches=customer_matches,
            recommendation=recommendation,
            suggested_action=suggested_action,
        )

    @classmethod
    def merge_leads(
        cls,
        db: Session,
        request: LeadMergeRequest,
        current_user: User,
    ) -> Lead:
        """
        Gộp Lead trùng lặp (Lead-to-Lead) trong Database Transaction:
        - Chuyển toàn bộ Activities từ duplicate_lead sang primary_lead.
        - Cập nhật thông tin được chỉ định hoặc nối tiếp ghi chú.
        - Đánh dấu duplicate_lead là MERGED, lưu merged_into_lead_id.
        - Tự động sinh Activity và AuditLog ghi vết hệ thống.
        """
        if request.primary_lead_id == request.duplicate_lead_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lead chính và Lead trùng lặp không thể là cùng một bản ghi.",
            )

        primary = db.query(Lead).filter(Lead.id == request.primary_lead_id).first()
        if not primary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy Lead chính với ID: {request.primary_lead_id}",
            )

        duplicate = db.query(Lead).filter(Lead.id == request.duplicate_lead_id).first()
        if not duplicate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy Lead trùng lặp với ID: {request.duplicate_lead_id}",
            )

        if duplicate.status == "MERGED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lead này đã được gộp vào lead khác từ trước đó và không thể gộp lại.",
            )

        now = datetime.utcnow()

        try:
            # 1. Bảo toàn lịch sử: Điều chuyển toàn bộ Activities của Lead phụ sang Lead chính
            db.query(Activity).filter(Activity.lead_id == duplicate.id).update(
                {"lead_id": primary.id},
                synchronize_session=False,
            )

            # 2. Cập nhật các trường thông tin được chỉ định giữ lại (selected_fields)
            if request.selected_fields:
                allowed_fields = {
                    "full_name",
                    "phone",
                    "email",
                    "company",
                    "source",
                    "interest_need",
                    "notes",
                }
                for field_name, field_val in request.selected_fields.items():
                    if (
                        field_name in allowed_fields
                        and field_val is not None
                        and hasattr(primary, field_name)
                    ):
                        setattr(primary, field_name, field_val)

            # 3. Nối tiếp ghi chú nếu có và chưa bị ghi đè
            if duplicate.notes and not (
                request.selected_fields and "notes" in request.selected_fields
            ):
                if primary.notes:
                    if duplicate.notes not in primary.notes:
                        primary.notes = (
                            f"{primary.notes}\n[Ghi chú từ Lead gộp {duplicate.id}]: "
                            f"{duplicate.notes}"
                        )
                else:
                    primary.notes = duplicate.notes

            # 4. Soft-delete Lead phụ (đánh dấu trạng thái MERGED)
            duplicate.status = "MERGED"
            duplicate.merged_into_lead_id = primary.id

            # 5. Tự động sinh Activity ghi vết hệ thống vào Lead chính
            merge_activity = Activity(
                id=str(uuid.uuid4()),
                lead_id=primary.id,
                customer_id=None,
                user_id=current_user.id,
                type="status_change",
                title="Gộp Lead trùng lặp thành công",
                description=(
                    f"Lead đã được gộp từ bản ghi '{duplicate.full_name}' ({duplicate.id}) "
                    f"vào lúc {now.strftime('%Y-%m-%d %H:%M:%S')} bởi {current_user.full_name}."
                ),
                created_at=now,
            )
            db.add(merge_activity)

            # 6. Ghi AuditLog
            audit = AuditLog(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                action="MERGE_LEAD",
                details=(
                    f"Gộp Lead: Master ID '{primary.id}' ({primary.full_name}) "
                    f"← Duplicate ID '{duplicate.id}' ({duplicate.full_name})"
                ),
                performed_by=current_user.full_name,
                user_name=current_user.full_name,
                user_email=current_user.email,
                target_type="Lead",
                target_id=primary.id,
                field_name="merge",
                old_value=duplicate.id,
                new_value=primary.id,
                created_at=now,
            )
            db.add(audit)

            db.commit()
            db.refresh(primary)
            return primary
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi giao dịch trong quá trình gộp Lead: {str(exc)}",
            )

    @classmethod
    def attach_to_customer(
        cls,
        db: Session,
        request: LeadAttachToCustomerRequest,
        current_user: User,
    ) -> Dict[str, Any]:
        """
        Gắn Lead trùng vào Khách hàng đã có trong CRM (Lead-to-Customer Matching):
        - Chuyển toàn bộ Activities của Lead sang Customer.
        - Cập nhật Lead: status = 'CONVERTED', converted_customer_id = customer.id.
        - Sinh Activity và AuditLog ghi vết tương tác trên Khách hàng.
        """
        lead = db.query(Lead).filter(Lead.id == request.lead_id).first()
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy Lead với ID: {request.lead_id}",
            )

        customer = (
            db.query(Customer)
            .filter(Customer.id == request.customer_id, Customer.is_deleted == False)
            .first()
        )
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy Khách hàng với ID: {request.customer_id}",
            )

        if lead.status == "MERGED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lead này đã được gộp vào lead khác từ trước đó và không thể gắn vào khách hàng.",
            )

        now = datetime.utcnow()

        try:
            # 1. Chuyển toàn bộ hoạt động (Activities) của Lead sang Customer
            db.query(Activity).filter(Activity.lead_id == lead.id).update(
                {"customer_id": customer.id, "lead_id": None},
                synchronize_session=False,
            )

            # 2. Cập nhật Lead thành trạng thái CONVERTED và gán converted_customer_id
            lead.status = "CONVERTED"
            lead.converted_customer_id = customer.id
            if request.notes:
                note_line = f"[Gắn vào Khách hàng {customer.id}]: {request.notes}"
                lead.notes = f"{lead.notes}\n{note_line}" if lead.notes else note_line

            # 3. Tạo Activity tại hồ sơ Khách hàng
            note_suffix = f" Ghi chú: {request.notes}" if request.notes else ""
            desc = (
                f"Đã gắn thông tin tương tác từ Lead '{lead.full_name}' (ID: {lead.id}, "
                f"SĐT: {lead.phone}, Nguồn: {lead.source}) vào khách hàng bởi {current_user.full_name}.{note_suffix}"
            )
            attach_activity = Activity(
                id=str(uuid.uuid4()),
                customer_id=customer.id,
                lead_id=None,
                user_id=current_user.id,
                type="status_change",
                title="Gắn tương tác từ Lead vào Khách hàng",
                description=desc,
                created_at=now,
            )
            db.add(attach_activity)

            # 4. Ghi AuditLog
            audit = AuditLog(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                action="ATTACH_LEAD_TO_CUSTOMER",
                details=(
                    f"Gắn Lead '{lead.full_name}' ({lead.id}) "
                    f"vào Khách hàng '{customer.company or customer.full_name}' ({customer.id})"
                ),
                performed_by=current_user.full_name,
                user_name=current_user.full_name,
                user_email=current_user.email,
                target_type="Lead",
                target_id=lead.id,
                field_name="converted_customer_id",
                old_value=None,
                new_value=customer.id,
                created_at=now,
            )
            db.add(audit)

            db.commit()
            db.refresh(lead)

            return {
                "message": "Đã gắn Lead vào Khách hàng thành công.",
                "lead_id": lead.id,
                "customer_id": customer.id,
                "status": lead.status,
                "lead": lead,
            }
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi giao dịch trong quá trình gắn Lead vào Khách hàng: {str(exc)}",
            )
