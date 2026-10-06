import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.customer import Customer, Contact
from app.models.activity import Activity, Note
from app.models.user import User
from app.schemas.customer import CreateCustomerDTO
from app.repositories.customer_repository import CustomerRepository


class CustomerService:
    """
    Tầng Service xử lý nghiệp vụ Quản lý Khách hàng 360°.
    Tuân thủ Clean Layered Architecture, Data Scope Security & 100% Type Hints.
    """

    @staticmethod
    def get_customers(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Customer], int]:
        """Lấy danh sách khách hàng được bảo vệ theo Data Scope."""
        return CustomerRepository.get_all(
            db=db,
            user=user,
            search=search,
            status=[status] if status and status.lower() != "all" else None,
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
        Tạo mới khách hàng.
        Luôn gán assigned_user_id là current_user server-side, không tin tưởng client input.
        """
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
            industry=dto.industry,
            company_size=dto.companySize,
            region=dto.region,
            tax_code=dto.taxCode,
            website=dto.website,
        )
        for contact_dto in dto.contacts:
            new_customer.contacts.append(
                Contact(
                    id=str(uuid.uuid4()),
                    full_name=contact_dto.fullName,
                    phone=contact_dto.phone,
                    email=contact_dto.email,
                    is_primary=int(contact_dto.isPrimary),
                )
            )
        return CustomerRepository.create(db, new_customer)

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
        # Xác minh khách hàng thuộc phạm vi cho phép trước khi ghi nhận
        CustomerRepository.get_scoped_by_id(db, customer_id, user)

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
        """Ghi nhận hoạt động khách hàng (xác thực quyền truy cập trước)."""
        # Xác minh khách hàng thuộc phạm vi cho phép trước khi thêm hoạt động
        CustomerRepository.get_scoped_by_id(db, customer_id, user)

        new_activity: Activity = Activity(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            user_id=user.id,
            type=activity_type,
            title=title,
            description=description,
        )
        return CustomerRepository.add_activity(db, new_activity)
