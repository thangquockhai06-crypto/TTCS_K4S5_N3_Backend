"""
Tầng Repository cơ sở (BaseRepository) triển khai Centralized Data Scope Filter.
Tuân thủ Clean Layered Architecture, PEP 8 và 100% Type Hints.
"""
from typing import Type, Any, Optional
from sqlalchemy.orm import Session, Query
from sqlalchemy import select, false

from app.models.user import User
from app.models.customer import Customer
from app.models.deal import Deal
from app.models.activity import Activity, Note
from app.models.quotation import Quotation
from app.core.scope import DataScope, get_user_data_scope
from fastapi import HTTPException, status


def get_model_owner_column(model: Type[Any]) -> Optional[Any]:
    """
    Xác định cột định danh người sở hữu / phụ trách của từng model CSDL:
    - Customer -> assigned_user_id
    - Deal -> owner_id
    - Activity -> user_id
    - Quotation -> owner_id
    - Note -> author_id
    """
    owner_map = {
        Customer: Customer.assigned_user_id,
        Deal: Deal.owner_id,
        Activity: Activity.user_id,
        Quotation: Quotation.owner_id,
        Note: Note.author_id,
    }
    if model in owner_map:
        return owner_map[model]

    # Kiểm tra động các thuộc tính phổ biến nếu model mở rộng
    for col_name in ["owner_id", "assigned_user_id", "user_id", "author_id", "created_by"]:
        if hasattr(model, col_name):
            return getattr(model, col_name)

    return None


def apply_data_scope_filter(
    query: Query,
    user: Optional[User],
    model: Type[Any],
) -> Query:
    """
    Hàm lọc truy vấn tập trung theo phạm vi dữ liệu (Centralized Data Scope Filter).
    Thực thi 100% ở tầng CSDL (SQLAlchemy Query level), không nạp dữ liệu vào Python để lọc.

    Nguyên tắc an toàn (Fail-Safe / Zero Trust):
    - Không có user hợp lệ -> Trả về truy vấn rỗng (false), không bao giờ mở toang dữ liệu.
    - OWN: record.owner == user.id
    - TEAM: record.owner thuộc danh sách thành viên cùng team (user.team_id).
            Nếu user chưa được gán team -> trả về rỗng, không fail open.
    - ALL: Không giới hạn quyền sở hữu dữ liệu.
    """
    if user is None:
        return query.filter(false())

    scope: DataScope = get_user_data_scope(user)

    # 1. Phạm vi ALL: Xem toàn bộ dữ liệu
    if scope == DataScope.ALL:
        return query

    owner_col = get_model_owner_column(model)
    if owner_col is None:
        # Nếu model không có cột sở hữu -> bảo toàn query
        return query

    # 2. Phạm vi OWN: Chỉ bản ghi do chính mình tạo / được phân công
    if scope == DataScope.OWN:
        return query.filter(owner_col == user.id)

    # 3. Phạm vi TEAM: Bản ghi thuộc thành viên trong cùng nhóm
    if scope == DataScope.TEAM:
        team_id = getattr(user, "team_id", None)
        if not team_id or not str(team_id).strip():
            # Người dùng chưa thuộc nhóm nào -> Không được truy cập dữ liệu nhóm (Fail-closed)
            return query.filter(false())

        # Subquery lấy ID của các thành viên trong cùng team_id
        team_users_subquery = (
            select(User.id)
            .where(User.team_id == team_id)
            .scalar_subquery()
        )
        return query.filter(owner_col.in_(team_users_subquery))

    # Mặc định an toàn
    return query.filter(false())


class BaseRepository:
    """
    Lớp Repository cơ sở chứa các tiện ích phân quyền tập trung.
    """

    @staticmethod
    def apply_data_scope_filter(
        query: Query,
        user: Optional[User],
        model: Type[Any],
    ) -> Query:
        """Phương thức lọc dữ liệu tập trung theo phạm vi người dùng."""
        return apply_data_scope_filter(query=query, user=user, model=model)

    @staticmethod
    def get_scoped_record_or_raise(
        db: Session,
        model: Type[Any],
        record_id: str,
        user: User,
        not_found_msg: str = "Không tìm thấy dữ liệu.",
        forbidden_msg: str = "Bạn không có quyền truy cập dữ liệu này.",
    ) -> Any:
        """
        Bảo vệ truy cập chi tiết từng bản ghi đơn lẻ (Single Record Access Protection).
        - Nếu bản ghi hoàn toàn không tồn tại trong CSDL -> HTTP 404
        - Nếu bản ghi tồn tại nhưng nằm ngoài Data Scope của user -> HTTP 403 Forbidden
        - Nếu bản ghi hợp lệ trong phạm vi -> Trả về bản ghi
        """
        # 1. Kiểm tra tồn tại trong CSDL (unscoped)
        unscoped_record = db.query(model).filter(model.id == record_id).first()
        if not unscoped_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_msg,
            )

        # 2. Kiểm tra quyền truy cập thông qua Centralized Data Scope Filter
        scoped_query = BaseRepository.apply_data_scope_filter(
            query=db.query(model),
            user=user,
            model=model,
        )
        scoped_record = scoped_query.filter(model.id == record_id).first()

        if not scoped_record:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=forbidden_msg,
            )

        return scoped_record
