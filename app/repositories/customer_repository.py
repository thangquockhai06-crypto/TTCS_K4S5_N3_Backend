from typing import Optional, List, Tuple, Sequence
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_, and_, exists, false

from app.models.customer import Customer, Contact
from app.models.activity import Activity, Note
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from app.core.customer_search import escape_like, normalize_phone, normalize_text, normalize_tax_code


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
        status: Optional[Sequence[str]] = None,
        industry: Optional[Sequence[str]] = None,
        company_size: Optional[Sequence[str]] = None,
        region: Optional[Sequence[str]] = None,
        owner_ids: Optional[Sequence[str]] = None,
        include_unassigned: bool = False,
        sort: str = "created_at",
        descending: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Customer], int]:
        query = db.query(Customer)
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Customer)

        if search and search.strip():
            normalized_query = normalize_text(search)
            normalized_tax = normalize_tax_code(search)
            normalized_phone = normalize_phone(search)
            predicates = []
            if normalized_query:
                predicates.append(Customer.normalized_name.like(f"%{escape_like(normalized_query)}%", escape="\\"))
            if normalized_tax:
                predicates.append(Customer.normalized_tax_code.like(f"{escape_like(normalized_tax)}%", escape="\\"))
            raw_pattern = f"%{escape_like(search.strip())}%"
            predicates.extend(
                [
                    Customer.email.ilike(raw_pattern, escape="\\"),
                    Customer.phone.ilike(raw_pattern, escape="\\"),
                    Customer.company.ilike(raw_pattern, escape="\\"),
                ]
            )
            if normalized_phone:
                phone_pattern = f"%{escape_like(normalized_phone)}%"
                predicates.extend(
                    [
                        Customer.normalized_phone.like(phone_pattern, escape="\\"),
                        exists().where(
                            and_(
                                Contact.customer_id == Customer.id,
                                Contact.normalized_phone.like(phone_pattern, escape="\\"),
                            )
                        ),
                    ]
                )
            query = query.filter(or_(*predicates) if predicates else false())

        if status:
            query = query.filter(Customer.status.in_(list(status)))
        if industry:
            query = query.filter(Customer.industry.in_(list(industry)))
        if company_size:
            query = query.filter(Customer.company_size.in_(list(company_size)))
        if region:
            query = query.filter(Customer.region.in_(list(region)))
        if owner_ids or include_unassigned:
            owner_predicates = []
            if owner_ids:
                owner_predicates.append(Customer.assigned_user_id.in_(list(owner_ids)))
            if include_unassigned:
                owner_predicates.append(Customer.assigned_user_id.is_(None))
            query = query.filter(or_(*owner_predicates))

        total = query.count()
        sort_columns = {
            "name": Customer.normalized_name,
            "created_at": Customer.created_at,
            "status": Customer.status,
            "owner": Customer.assigned_user_id,
            "industry": Customer.industry,
            "company_size": Customer.company_size,
            "region": Customer.region,
        }
        sort_column = sort_columns.get(sort, Customer.created_at)
        direction = sort_column.desc() if descending else sort_column.asc()
        query = query.options(
            joinedload(Customer.assigned_user),
            selectinload(Customer.contacts),
        )
        customers = query.order_by(direction, Customer.id.asc()).offset(skip).limit(limit).all()
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
        return (
            db.query(Customer)
            .options(joinedload(Customer.assigned_user))
            .filter(Customer.id == customer_id)
            .first()
        )

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
