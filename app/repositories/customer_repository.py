from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

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
        industry: Optional[str] = None,
        tier: Optional[str] = None,
        owner_id: Optional[str] = None,
        risk_only: Optional[bool] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Customer], int]:
        """
        Lấy danh sách khách hàng có phân trang, tìm kiếm nâng cao và lọc động.
        LUÔN áp dụng Centralized Data Scope Filter ở mức câu lệnh CSDL.
        Loại trừ các bản ghi đã xóa mềm (is_deleted == False).
        """
        query = db.query(Customer).filter(Customer.is_deleted == False)

        # 1. Áp dụng Data Scope Filter trước tiên
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Customer)

        # 2. Tìm kiếm đa trường (Công ty, MST, SĐT, Email, Tên đại diện)
        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Customer.full_name.ilike(search_pattern),
                    Customer.email.ilike(search_pattern),
                    Customer.phone.ilike(search_pattern),
                    Customer.company.ilike(search_pattern),
                    Customer.tax_code.ilike(search_pattern),
                )
            )

        # 3. Lọc theo trạng thái
        if status and status.lower() != "all":
            query = query.filter(Customer.status == status.lower())

        # 4. Lọc nâng cao (S3-07)
        if industry and industry.strip() and industry.lower() != "all":
            query = query.filter(Customer.industry.ilike(f"%{industry.strip()}%"))

        if tier and tier.strip() and tier.lower() != "all":
            query = query.filter(Customer.tier.ilike(f"%{tier.strip()}%"))

        if owner_id and owner_id.strip() and owner_id.lower() != "all":
            from app.core.scope import get_user_data_scope, DataScope
            if user is None or get_user_data_scope(user) != DataScope.OWN:
                query = query.filter(Customer.assigned_user_id == owner_id.strip())

        if risk_only:
            query = query.filter(Customer.risk_flag == True)

        if min_value is not None:
            query = query.filter(Customer.total_contract_value >= min_value)

        if max_value is not None:
            query = query.filter(Customer.total_contract_value <= max_value)

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
        """
        query = db.query(Customer).filter(Customer.is_deleted == False)
        query = BaseRepository.apply_data_scope_filter(query, user, Customer)

        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Customer.full_name.ilike(search_pattern),
                    Customer.email.ilike(search_pattern),
                    Customer.phone.ilike(search_pattern),
                    Customer.company.ilike(search_pattern),
                    Customer.tax_code.ilike(search_pattern),
                )
            )

        if status and status.lower() != "all":
            query = query.filter(Customer.status == status.lower())

        return query.order_by(Customer.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, customer_id: str) -> Optional[Customer]:
        """Truy vấn khách hàng theo ID không kiểm tra scope (Dùng nội bộ)."""
        return db.query(Customer).filter(
            Customer.id == customer_id,
            Customer.is_deleted == False,
        ).first()

    @staticmethod
    def get_by_id_include_deleted(db: Session, customer_id: str) -> Optional[Customer]:
        """Truy vấn khách hàng theo ID bao gồm cả đã xóa mềm."""
        return db.query(Customer).filter(Customer.id == customer_id).first()

    @staticmethod
    def get_by_tax_code(db: Session, tax_code: str) -> Optional[Customer]:
        """Tìm khách hàng theo Mã số thuế (MST)."""
        if not tax_code or not str(tax_code).strip():
            return None
        return db.query(Customer).filter(
            Customer.tax_code == str(tax_code).strip(),
            Customer.is_deleted == False,
        ).first()

    @staticmethod
    def get_scoped_by_id(db: Session, customer_id: str, user: User) -> Customer:
        """
        Truy vấn chi tiết khách hàng có bảo vệ phân quyền phạm vi:
        - Không tồn tại hoặc đã xóa mềm -> HTTP 404
        - Tồn tại nhưng không thuộc quyền hạn -> HTTP 403 Forbidden
        """
        customer = db.query(Customer).filter(
            Customer.id == customer_id,
            Customer.is_deleted == False,
        ).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy khách hàng.",
            )

        scoped_query = BaseRepository.apply_data_scope_filter(
            query=db.query(Customer).filter(Customer.is_deleted == False),
            user=user,
            model=Customer,
        )
        scoped_customer = scoped_query.filter(Customer.id == customer_id).first()
        if not scoped_customer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập dữ liệu này.",
            )
        return scoped_customer

    @staticmethod
    def create(db: Session, customer: Customer) -> Customer:
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def update(db: Session, customer: Customer, update_data: Dict[str, Any]) -> Customer:
        """Cập nhật thông tin khách hàng từ từ điển thuộc tính."""
        for key, value in update_data.items():
            if hasattr(customer, key) and value is not None:
                setattr(customer, key, value)
        customer.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def soft_delete(db: Session, customer: Customer) -> None:
        """Xóa mềm khách hàng (đặt cờ is_deleted = True)."""
        customer.is_deleted = True
        customer.updated_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def update_status(db: Session, customer: Customer, new_status: str) -> Customer:
        customer.status = new_status
        customer.updated_at = datetime.utcnow()
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
    def get_stagnant(
        db: Session,
        cutoff_date: datetime,
        user: Optional[User] = None,
        limit: int = 100,
    ) -> List[Customer]:
        """
        S3-09: Truy vấn danh sách khách hàng cần chăm sóc định kỳ:
        - last_interaction_at < cutoff_date HOẶC last_interaction_at IS NULL
        - Sắp xếp ưu tiên: total_contract_value giảm dần
        - Tuân thủ Data Scope Filter
        """
        query = db.query(Customer).filter(Customer.is_deleted == False)

        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Customer)

        query = query.filter(
            or_(
                Customer.last_interaction_at < cutoff_date,
                Customer.last_interaction_at.is_(None),
            )
        )

        return query.order_by(desc(Customer.total_contract_value)).limit(limit).all()

    @staticmethod
    def get_children(db: Session, parent_id: str) -> List[Customer]:
        """Lấy danh sách công ty con trực tiếp của một công ty."""
        return db.query(Customer).filter(
            Customer.parent_customer_id == parent_id,
            Customer.is_deleted == False,
        ).all()

    @staticmethod
    def is_descendant(db: Session, root_id: str, target_id: str) -> bool:
        """
        Kiểm tra xem target_id có phải là hậu duệ (con/cháu/...) của root_id hay không.
        Dùng để chống vòng lặp cha - con (Circular Reference Prevention).
        """
        if root_id == target_id:
            return True

        visited: Set[str] = set()
        queue = [root_id]

        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)

            children = db.query(Customer.id).filter(
                Customer.parent_customer_id == curr,
                Customer.is_deleted == False,
            ).all()

            for (child_id,) in children:
                if child_id == target_id:
                    return True
                if child_id not in visited:
                    queue.append(child_id)

        return False

    @staticmethod
    def count_all(db: Session, user: Optional[User] = None) -> int:
        query = db.query(Customer).filter(Customer.is_deleted == False)
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Customer)
        return query.count()

    @staticmethod
    def count_by_status(db: Session, status: str, user: Optional[User] = None) -> int:
        query = db.query(Customer).filter(Customer.is_deleted == False)
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Customer)
        return query.filter(Customer.status == status.lower()).count()
