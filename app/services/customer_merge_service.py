import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.customer import Customer
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.activity import Activity, Note
from app.models.support_ticket import SupportTicket
from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository


class CustomerMergeService:
    """
    Service xử lý Gộp khách hàng trùng lặp S3-04 (Merge Duplicate Customers).
    - Thực thi trong Transaction đảm bảo toàn vẹn dữ liệu (ACID).
    - Điều chuyển toàn bộ Contact, Deal, Activity, Note, SupportTicket sang bản ghi Master.
    - Cập nhật giá trị hợp đồng lũy kế.
    - Xóa mềm (soft-delete) khách hàng trùng lặp.
    - Ghi nhận AuditLog và Activity phục vụ truy vết.
    """

    @staticmethod
    def merge_customers(
        db: Session,
        master_id: str,
        duplicate_id: str,
        user: User,
        field_overrides: Optional[Dict[str, Any]] = None,
    ) -> Customer:
        if master_id == duplicate_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Khách hàng chính và khách hàng trùng lặp không thể là cùng một bản ghi.",
            )

        # 1. Kiểm tra phân quyền truy cập cho cả 2 bản ghi
        master = CustomerRepository.get_scoped_by_id(db, master_id, user)
        duplicate = CustomerRepository.get_scoped_by_id(db, duplicate_id, user)

        if duplicate.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Khách hàng trùng lặp đã bị xóa hoặc đã được gộp trước đó.",
            )

        master_name = master.company or master.full_name
        dup_name = duplicate.company or duplicate.full_name

        # 2. Bắt đầu Transaction bảo vệ tính nhất quán dữ liệu
        try:
            # 2.1. Điều chuyển Contacts
            db.query(Contact).filter(Contact.customer_id == duplicate.id).update(
                {"customer_id": master.id, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )

            # 2.2. Điều chuyển Deals
            db.query(Deal).filter(Deal.customer_id == duplicate.id).update(
                {"customer_id": master.id, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )

            # 2.3. Điều chuyển Activities
            db.query(Activity).filter(Activity.customer_id == duplicate.id).update(
                {"customer_id": master.id},
                synchronize_session=False,
            )

            # 2.4. Điều chuyển Notes
            db.query(Note).filter(Note.customer_id == duplicate.id).update(
                {"customer_id": master.id},
                synchronize_session=False,
            )

            # 2.5. Điều chuyển Support Tickets
            db.query(SupportTicket).filter(SupportTicket.customer_id == duplicate.id).update(
                {"customer_id": master.id, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )

            # 2.6. Điều chuyển các công ty con (nếu có)
            db.query(Customer).filter(Customer.parent_customer_id == duplicate.id).update(
                {"parent_customer_id": master.id, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )

            # 2.7. Ghi đè các trường nếu người dùng chọn trường từ duplicate
            if field_overrides:
                for field_key, chosen_val in field_overrides.items():
                    if hasattr(master, field_key) and chosen_val is not None:
                        setattr(master, field_key, chosen_val)

            # 2.8. Cộng dồn giá trị hợp đồng
            master.total_contract_value = float(master.total_contract_value or 0.0) + float(
                duplicate.total_contract_value or 0.0
            )

            # 2.9. Xóa mềm duplicate và giải phóng tax_code trùng để tránh vi phạm unique index
            duplicate.tax_code = None
            duplicate.is_deleted = True
            duplicate.updated_at = datetime.utcnow()

            # 2.10. Ghi Activity vào Master
            merge_activity = Activity(
                id=str(uuid.uuid4()),
                customer_id=master.id,
                user_id=user.id,
                type="status_change",
                title="Gộp khách hàng trùng lặp thành công",
                description=(
                    f"Đã gộp toàn bộ dữ liệu từ khách hàng '{dup_name}' (ID: {duplicate.id}) "
                    f"vào khách hàng '{master_name}'. Người thực hiện: {user.full_name}."
                ),
                created_at=datetime.utcnow(),
            )
            db.add(merge_activity)

            # 2.11. Ghi AuditLog
            audit = AuditLog(
                id=str(uuid.uuid4()),
                user_id=user.id,
                action="MERGE_CUSTOMER",
                details=(
                    f"Gộp khách hàng: Master ID '{master.id}' ({master_name}) "
                    f"← Duplicate ID '{duplicate.id}' ({dup_name})"
                ),
                performed_by=user.full_name,
                user_name=user.full_name,
                user_email=user.email,
                target_type="Customer",
                target_id=master.id,
                field_name="merge",
                old_value=duplicate.id,
                new_value=master.id,
                created_at=datetime.utcnow(),
            )
            db.add(audit)

            # Commit toàn bộ transaction
            db.commit()
            db.refresh(master)
            return master

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Quá trình gộp khách hàng thất bại và đã hoàn tác: {str(e)}",
            )

    @staticmethod
    def find_potential_duplicates(
        db: Session,
        user: User,
    ) -> List[Dict[str, Any]]:
        """
        Tìm danh sách các cặp khách hàng có nguy cơ trùng lặp (trùng MST, SĐT hoặc Tên công ty).
        """
        scoped_customers, _ = CustomerRepository.get_all(db=db, user=user, limit=500)
        duplicates: List[Dict[str, Any]] = []

        seen_mst: Dict[str, Customer] = {}
        seen_phone: Dict[str, Customer] = {}
        seen_company: Dict[str, Customer] = {}

        for c in scoped_customers:
            # So khớp MST
            if c.tax_code and c.tax_code.strip():
                mst = c.tax_code.strip()
                if mst in seen_mst:
                    duplicates.append({
                        "reason": f"Trùng Mã số thuế ({mst})",
                        "customerA": seen_mst[mst],
                        "customerB": c,
                    })
                else:
                    seen_mst[mst] = c

            # So khớp SĐT
            if c.phone and c.phone.strip():
                phone = c.phone.strip()
                if phone in seen_phone:
                    duplicates.append({
                        "reason": f"Trùng Số điện thoại ({phone})",
                        "customerA": seen_phone[phone],
                        "customerB": c,
                    })
                else:
                    seen_phone[phone] = c

            # So khớp tên công ty
            if c.company and c.company.strip() and len(c.company.strip()) > 3:
                comp = c.company.strip().lower()
                if comp in seen_company:
                    duplicates.append({
                        "reason": f"Trùng Tên doanh nghiệp ('{c.company}')",
                        "customerA": seen_company[comp],
                        "customerB": c,
                    })
                else:
                    seen_company[comp] = c

        return duplicates
