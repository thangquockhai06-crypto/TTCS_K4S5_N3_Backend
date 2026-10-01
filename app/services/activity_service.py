import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.user import User
from app.schemas.activity import CreateActivityDTO
from app.repositories.activity_repository import ActivityRepository
from app.repositories.customer_repository import CustomerRepository


class ActivityService:
    """
    Tầng Service xử lý nghiệp vụ Hoạt động (Activities).
    Tuân thủ Clean Layered Architecture, Data Scope Security & 100% Type Hints.
    """

    @staticmethod
    def get_activities(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        activity_type: Optional[str] = None,
        customer_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Activity], int]:
        """Lấy danh sách hoạt động tuân thủ Data Scope."""
        return ActivityRepository.get_all(
            db=db,
            user=user,
            search=search,
            activity_type=activity_type,
            customer_id=customer_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_activities_for_export(
        db: Session,
        user: User,
        search: Optional[str] = None,
        activity_type: Optional[str] = None,
    ) -> List[Activity]:
        """Lấy danh sách hoạt động trong Data Scope để xuất Excel."""
        return ActivityRepository.get_all_for_export(
            db=db,
            user=user,
            search=search,
            activity_type=activity_type,
        )

    @staticmethod
    def get_activity_by_id(
        db: Session,
        activity_id: str,
        user: Optional[User] = None,
    ) -> Optional[Activity]:
        """
        Lấy chi tiết hoạt động. Bắt buộc kiểm tra quyền (403 Forbidden nếu không có quyền).
        """
        if user is not None:
            return ActivityRepository.get_scoped_by_id(db, activity_id, user)
        return ActivityRepository.get_by_id(db, activity_id)

    @staticmethod
    def create_activity(
        db: Session,
        dto: CreateActivityDTO,
        user: User,
    ) -> Activity:
        """
        Tạo mới hoạt động.
        Xác thực quyền xem khách hàng trước và luôn gán user_id = user.id.
        """
        # Xác thực quyền truy cập khách hàng trước
        CustomerRepository.get_scoped_by_id(db, dto.customerId, user)

        new_activity = Activity(
            id=str(uuid.uuid4()),
            customer_id=dto.customerId,
            user_id=user.id,
            type=dto.type,
            title=dto.title,
            description=dto.description or "",
        )
        return ActivityRepository.create(db, new_activity)
