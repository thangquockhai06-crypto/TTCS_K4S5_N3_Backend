from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.quotation import Quotation
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class QuotationRepository(BaseRepository):
    """
    Tầng Repository xử lý truy vấn dữ liệu Báo giá (Quotations).
    Tích hợp Centralized Data Scope Filter ở mức CSDL.
    Tuân thủ Clean Layered Architecture & 100% Type Hints.
    """

    @staticmethod
    def get_all(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Quotation], int]:
        """Lấy danh sách báo giá thỏa mãn Data Scope của người dùng."""
        query = db.query(Quotation)

        # 1. Lọc theo Data Scope
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Quotation)

        # 2. Tìm kiếm theo tiêu đề hoặc mã báo giá
        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                Quotation.title.ilike(search_pattern) | Quotation.quote_number.ilike(search_pattern)
            )

        # 3. Lọc theo trạng thái
        if status and status.lower() != "all":
            query = query.filter(Quotation.status == status.lower())

        # 4. Lọc theo khách hàng
        if customer_id:
            query = query.filter(Quotation.customer_id == customer_id)

        total = query.count()
        quotations = query.order_by(Quotation.created_at.desc()).offset(skip).limit(limit).all()
        return quotations, total

    @staticmethod
    def get_all_for_export(
        db: Session,
        user: User,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Quotation]:
        """Lấy danh sách báo giá trong Data Scope để xuất Excel."""
        query = db.query(Quotation)
        query = BaseRepository.apply_data_scope_filter(query, user, Quotation)

        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                Quotation.title.ilike(search_pattern) | Quotation.quote_number.ilike(search_pattern)
            )

        if status and status.lower() != "all":
            query = query.filter(Quotation.status == status.lower())

        return query.order_by(Quotation.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, quotation_id: str) -> Optional[Quotation]:
        """Truy vấn báo giá theo ID không kiểm tra scope (Dùng nội bộ)."""
        return db.query(Quotation).filter(Quotation.id == quotation_id).first()

    @staticmethod
    def get_scoped_by_id(db: Session, quotation_id: str, user: User) -> Quotation:
        """
        Truy vấn chi tiết Báo giá có bảo vệ Data Scope:
        - Không tồn tại -> HTTP 404
        - Tồn tại nhưng không thuộc quyền hạn -> HTTP 403 Forbidden
        """
        return BaseRepository.get_scoped_record_or_raise(
            db=db,
            model=Quotation,
            record_id=quotation_id,
            user=user,
            not_found_msg="Không tìm thấy báo giá.",
            forbidden_msg="Bạn không có quyền truy cập dữ liệu này.",
        )

    @staticmethod
    def create(db: Session, quotation: Quotation) -> Quotation:
        db.add(quotation)
        db.commit()
        db.refresh(quotation)
        return quotation
