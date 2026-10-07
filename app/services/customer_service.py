import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.activity import Activity, Note
from app.models.user import User
from app.schemas.customer import CreateCustomerDTO, UpdateCustomerDTO
from app.repositories.customer_repository import CustomerRepository


class CustomerService:
    """
    Tầng Service xử lý nghiệp vụ Quản lý Khách hàng 360° (EP-03).
    Tuân thủ Clean Layered Architecture, Data Scope Security & 100% Type Hints.
    """

    @staticmethod
    def get_customers(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        industry: Optional[str] = None,
        tier: Optional[str] = None,
        owner_id: Optional[str] = None,
        risk_only: Optional[bool] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Customer], int]:
        """Lấy danh sách khách hàng được bảo vệ theo Data Scope với bộ lọc nâng cao."""
        return CustomerRepository.get_all(
            db=db,
            user=user,
            search=search,
            status=status,
            industry=industry,
            tier=tier,
            owner_id=owner_id,
            risk_only=risk_only,
            min_value=min_value,
            max_value=max_value,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_customers_for_export(
        db: Session,
        user: User,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Customer]:
        """Lấy toàn bộ khách hàng trong phạm vi quyền hạn để xuất Excel."""
        return CustomerRepository.get_all_for_export(
            db=db,
            user=user,
            search=search,
            status=status,
        )

    @staticmethod
    def get_customer_by_id(
        db: Session,
        customer_id: str,
        user: Optional[User] = None,
    ) -> Optional[Customer]:
        """
        Lấy chi tiết khách hàng. Nếu có user, bắt buộc kiểm tra quyền (403 Forbidden nếu không có quyền).
        """
        if user is not None:
            return CustomerRepository.get_scoped_by_id(db, customer_id, user)
        return CustomerRepository.get_by_id(db, customer_id)

    @staticmethod
    def create_customer(
        db: Session,
        dto: CreateCustomerDTO,
        user: User,
    ) -> Customer:
        """
        Tạo mới khách hàng doanh nghiệp S3-01.
        Kiểm tra tính duy nhất của Mã số thuế (MST/tax_code).
        """
        # 1. Kiểm tra tính duy nhất của Mã số thuế
        if dto.taxCode and str(dto.taxCode).strip():
            existing_mst = CustomerRepository.get_by_tax_code(db, dto.taxCode.strip())
            if existing_mst:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mã số thuế '{dto.taxCode}' đã tồn tại cho doanh nghiệp '{existing_mst.company or existing_mst.full_name}'."
                )

        new_customer: Customer = Customer(
            id=str(uuid.uuid4()),
            full_name=dto.fullName,
            email=dto.email,
            phone=dto.phone,
            company=dto.company or "",
            status=dto.status or "lead",
            health_score=dto.healthScore or 85,
            assigned_user_id=user.id,
            avatar_url=f"https://api.dicebear.com/7.x/initials/svg?seed={dto.fullName}",
            tax_code=dto.taxCode.strip() if dto.taxCode else None,
            parent_customer_id=dto.parentCustomerId if dto.parentCustomerId else None,
            total_contract_value=dto.totalContractValue or 0.0,
            last_interaction_at=datetime.utcnow(),
            risk_flag=dto.riskFlag or False,
            risk_reason=dto.riskReason,
            industry=dto.industry or "",
            tier=dto.tier or "Enterprise",
            location=dto.location or "",
            website=dto.website or "",
            notes_summary=dto.summary or "",
        )
        return CustomerRepository.create(db, new_customer)

    @staticmethod
    def update_customer(
        db: Session,
        customer_id: str,
        dto: UpdateCustomerDTO,
        user: User,
    ) -> Customer:
        """Cập nhật thông tin khách hàng, kiểm tra quyền và tính duy nhất của MST."""
        customer = CustomerRepository.get_scoped_by_id(db, customer_id, user)

        # Kiểm tra trùng lặp MST nếu người dùng đổi MST sang giá trị mới
        if dto.taxCode and dto.taxCode.strip():
            existing_mst = CustomerRepository.get_by_tax_code(db, dto.taxCode.strip())
            if existing_mst and existing_mst.id != customer.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mã số thuế '{dto.taxCode}' đã tồn tại cho doanh nghiệp '{existing_mst.company or existing_mst.full_name}'."
                )

        update_dict: Dict[str, Any] = {}
        if dto.fullName is not None:
            update_dict["full_name"] = dto.fullName
        if dto.email is not None:
            update_dict["email"] = dto.email
        if dto.phone is not None:
            update_dict["phone"] = dto.phone
        if dto.company is not None:
            update_dict["company"] = dto.company
        if dto.status is not None:
            update_dict["status"] = dto.status
        if dto.healthScore is not None:
            update_dict["health_score"] = dto.healthScore
        if dto.taxCode is not None:
            update_dict["tax_code"] = dto.taxCode.strip() if dto.taxCode.strip() else None
        if dto.parentCustomerId is not None:
            update_dict["parent_customer_id"] = dto.parentCustomerId if dto.parentCustomerId.strip() else None
        if dto.totalContractValue is not None:
            update_dict["total_contract_value"] = dto.totalContractValue
        if dto.riskFlag is not None:
            update_dict["risk_flag"] = dto.riskFlag
        if dto.riskReason is not None:
            update_dict["risk_reason"] = dto.riskReason
        if dto.industry is not None:
            update_dict["industry"] = dto.industry
        if dto.tier is not None:
            update_dict["tier"] = dto.tier
        if dto.location is not None:
            update_dict["location"] = dto.location
        if dto.website is not None:
            update_dict["website"] = dto.website
        if dto.notesSummary is not None:
            update_dict["notes_summary"] = dto.notesSummary

        return CustomerRepository.update(db, customer, update_dict)

    @staticmethod
    def delete_customer(
        db: Session,
        customer_id: str,
        user: User,
    ) -> None:
        """Xóa mềm khách hàng (soft-delete)."""
        customer = CustomerRepository.get_scoped_by_id(db, customer_id, user)
        CustomerRepository.soft_delete(db, customer)

    @staticmethod
    def update_status(
        db: Session,
        customer_id: str,
        new_status: str,
        user: Optional[User] = None,
    ) -> Optional[Customer]:
        """Cập nhật trạng thái khách hàng (yêu cầu quyền truy cập bản ghi)."""
        if user is not None:
            customer = CustomerRepository.get_scoped_by_id(db, customer_id, user)
        else:
            customer = CustomerRepository.get_by_id(db, customer_id)

        if not customer:
            return None
        return CustomerRepository.update_status(db, customer, new_status)

    @staticmethod
    def add_note(
        db: Session,
        customer_id: str,
        content: str,
        user: User,
    ) -> Note:
        """Thêm ghi chú cho khách hàng (xác thực quyền truy cập trước)."""
        customer = CustomerRepository.get_scoped_by_id(db, customer_id, user)

        new_note: Note = Note(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            author_id=user.id,
            content=content,
        )
        return CustomerRepository.add_note(db, new_note)

    @staticmethod
    def add_activity(
        db: Session,
        customer_id: str,
        activity_type: str,
        title: str,
        description: str,
        user: User,
    ) -> Activity:
        """Ghi nhận hoạt động khách hàng (cập nhật last_interaction_at)."""
        customer = CustomerRepository.get_scoped_by_id(db, customer_id, user)

        # Cập nhật thời điểm tương tác gần nhất
        customer.last_interaction_at = datetime.utcnow()
        db.commit()

        new_activity: Activity = Activity(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            user_id=user.id,
            type=activity_type,
            title=title,
            description=description,
        )
        return CustomerRepository.add_activity(db, new_activity)

    @staticmethod
    def get_stagnant_customers(
        db: Session,
        user: User,
        days: int = 30,
        limit: int = 100,
    ) -> List[Customer]:
        """S3-09: Lấy danh sách khách hàng không tương tác > days ngày."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return CustomerRepository.get_stagnant(
            db=db,
            cutoff_date=cutoff_date,
            user=user,
            limit=limit,
        )

    @staticmethod
    def quick_touch(
        db: Session,
        customer_id: str,
        user: User,
    ) -> Customer:
        """
        S3-09: Thao tác nhanh "Đã liên hệ" (Quick Touch):
        - Cập nhật thời điểm last_interaction_at = utcnow()
        - Tự động ghi 1 Activity dạng "call" vào nhật ký hệ thống
        - Trả về thông tin khách hàng mới nhất
        """
        customer = CustomerRepository.get_scoped_by_id(db, customer_id, user)

        now = datetime.utcnow()
        customer.last_interaction_at = now
        db.commit()

        # Tạo bản ghi tương tác thực tế
        activity = Activity(
            id=str(uuid.uuid4()),
            customer_id=customer.id,
            user_id=user.id,
            type="call",
            title="Chăm sóc định kỳ nhanh (Quick Touch)",
            description=f"Nhân viên {user.full_name} đã thực hiện liên hệ chăm sóc định kỳ cho khách hàng {customer.company or customer.full_name}.",
            created_at=now,
        )
        CustomerRepository.add_activity(db, activity)
        db.refresh(customer)
        return customer
