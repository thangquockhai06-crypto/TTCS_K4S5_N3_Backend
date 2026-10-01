from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class ActivityRepository(BaseRepository):
    """
    Tầng Repository xử lý truy vấn dữ liệu Hoạt động (Activities).
    Tích hợp Centralized Data Scope Filter ở mức CSDL.
    Tuân thủ Clean Layered Architecture & 100% Type Hints.
    """

    @staticmethod
    def get_all(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        activity_type: Optional[str] = None,
        customer_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Activity], int]:
        """Lấy danh sách hoạt động thỏa mãn Data Scope của người dùng."""
        query = db.query(Activity)

        # 1. Lọc theo Data Scope
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Activity)

        # 2. Tìm kiếm theo tiêu đề / mô tả
        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                Activity.title.ilike(search_pattern) | Activity.description.ilike(search_pattern)
            )

        # 3. Lọc theo loại hoạt động
        if activity_type and activity_type.lower() != "all":
            query = query.filter(Activity.type == activity_type.lower())

        # 4. Lọc theo khách hàng
        if customer_id:
            query = query.filter(Activity.customer_id == customer_id)

        total = query.count()
        activities = query.order_by(Activity.created_at.desc()).offset(skip).limit(limit).all()
        return activities, total

    @staticmethod
    def get_all_for_export(
        db: Session,
        user: User,
        search: Optional[str] = None,
        activity_type: Optional[str] = None,
    ) -> List[Activity]:
        """Lấy danh sách hoạt động trong Data Scope để xuất Excel."""
        query = db.query(Activity)
        query = BaseRepository.apply_data_scope_filter(query, user, Activity)

        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                Activity.title.ilike(search_pattern) | Activity.description.ilike(search_pattern)
            )

        if activity_type and activity_type.lower() != "all":
            query = query.filter(Activity.type == activity_type.lower())

        return query.order_by(Activity.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, activity_id: str) -> Optional[Activity]:
        """Truy vấn hoạt động theo ID không kiểm tra scope (Dùng nội bộ)."""
        return db.query(Activity).filter(Activity.id == activity_id).first()

    @staticmethod
    def get_scoped_by_id(db: Session, activity_id: str, user: User) -> Activity:
        """
        Truy vấn chi tiết Hoạt động có bảo vệ Data Scope:
        - Không tồn tại -> HTTP 404
        - Tồn tại nhưng không thuộc quyền hạn -> HTTP 403 Forbidden
        """
        return BaseRepository.get_scoped_record_or_raise(
            db=db,
            model=Activity,
            record_id=activity_id,
            user=user,
            not_found_msg="Không tìm thấy hoạt động.",
            forbidden_msg="Bạn không có quyền truy cập dữ liệu này.",
        )

    @staticmethod
    def create(db: Session, activity: Activity) -> Activity:
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity
