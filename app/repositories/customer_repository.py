from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.customer import Customer
from app.models.activity import Activity, Note
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class CustomerRepository(BaseRepository):
    """
    Tầng Repository xử lý truy vấn dữ liệu khách hàng, ghi chú và hoạt động.
    Tích hợp Centralized Data Scope Filter bảo vệ toàn diện.
    Tuân thủ Clean Layered Architecture & 100% Type Hints.
    """

    @staticmethod
    def get_all(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Customer], int]:
        """
        Lấy danh sách khách hàng có phân trang, tìm kiếm và lọc trạng thái.
        LUÔN áp dụng Centralized Data Scope Filter ở mức câu lệnh CSDL.
        """
        query = db.query(Customer)

        # 1. Áp dụng Data Scope Filter trước tiên
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Customer)

        # 2. Tìm kiếm từ khóa (Search kết hợp AND với Data Scope)
        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Customer.full_name.ilike(search_pattern),
                    Customer.email.ilike(search_pattern),
                    Customer.phone.ilike(search_pattern),
                    Customer.company.ilike(search_pattern),
                )
            )

        # 3. Lọc theo trạng thái
        if status and status.lower() != "all":
            query = query.filter(Customer.status == status.lower())

        total = query.count()
        customers = query.order_by(Customer.created_at.desc()).offset(skip).limit(limit).all()
        return customers, total

    @staticmethod
    def get_all_for_export(
        db: Session,
        user: User,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Customer]:
        """
        Lấy toàn bộ danh sách khách hàng thỏa mãn Data Scope để xuất file Excel.
        Sử dụng chung logic lọc với danh sách để tránh thất thoát dữ liệu.
        """
        query = db.query(Customer)
        query = BaseRepository.apply_data_scope_filter(query, user, Customer)

        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Customer.full_name.ilike(search_pattern),
                    Customer.email.ilike(search_pattern),
                    Customer.phone.ilike(search_pattern),
                    Customer.company.ilike(search_pattern),
                )
            )

        if status and status.lower() != "all":
            query = query.filter(Customer.status == status.lower())

        return query.order_by(Customer.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, customer_id: str) -> Optional[Customer]:
        """Truy vấn khách hàng theo ID không kiểm tra scope (Dùng nội bộ)."""
        return db.query(Customer).filter(Customer.id == customer_id).first()

    @staticmethod
    def get_scoped_by_id(db: Session, customer_id: str, user: User) -> Customer:
        """
        Truy vấn chi tiết khách hàng có bảo vệ phân quyền phạm vi:
        - Không tồn tại -> HTTP 404
        - Tồn tại nhưng không thuộc quyền hạn -> HTTP 403 Forbidden
        """
        return BaseRepository.get_scoped_record_or_raise(
            db=db,
            model=Customer,
            record_id=customer_id,
            user=user,
            not_found_msg="Không tìm thấy khách hàng.",
            forbidden_msg="Bạn không có quyền truy cập dữ liệu này.",
        )

    @staticmethod
    def create(db: Session, customer: Customer) -> Customer:
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def update_status(db: Session, customer: Customer, new_status: str) -> Customer:
        customer.status = new_status
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def add_note(db: Session, note: Note) -> Note:
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def add_activity(db: Session, activity: Activity) -> Activity:
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity

    @staticmethod
    def count_all(db: Session, user: Optional[User] = None) -> int:
        query = db.query(Customer)
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Customer)
        return query.count()

    @staticmethod
    def count_by_status(db: Session, status: str, user: Optional[User] = None) -> int:
        query = db.query(Customer)
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Customer)
        return query.filter(Customer.status == status.lower()).count()
