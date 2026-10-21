import uuid
from typing import List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.user import User
from app.models.deal import Deal
from app.schemas.activity import CreateActivityDTO, ActivityDTO
from app.repositories.activity_repository import ActivityRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.deal_repository import DealRepository


class ActivityService:
    """
    Tầng Service xử lý nghiệp vụ Hoạt động (Activities & S6-05 Personal Activity History).
    Tuân thủ Clean Layered Architecture, Data Scope Security & 100% Type Hints.
    """

    @staticmethod
    def map_to_dto(a: Activity) -> ActivityDTO:
        cust_name = a.customer.full_name if a.customer else None
        deal_title = a.deal.title if a.deal else None
        user_name = a.user.full_name if a.user else None

        return ActivityDTO(
            id=a.id,
            customerId=a.customer_id,
            customerName=cust_name,
            dealId=a.deal_id,
            dealTitle=deal_title,
            userId=a.user_id,
            userName=user_name,
            type=a.type,
            title=a.title,
            description=a.description,
            notes=a.notes,
            createdAt=a.created_at.isoformat() if a.created_at else None,
        )

    @staticmethod
    def get_activities(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        activity_type: Optional[str] = None,
        customer_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        personal: bool = False,
        date_from: Optional[Any] = None,
        date_to: Optional[Any] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Activity], int]:
        """Lấy danh sách hoạt động tuân thủ Data Scope hoặc chỉ của cá nhân (S6-05)."""
        return ActivityRepository.get_all(
            db=db,
            user=user,
            search=search,
            activity_type=activity_type,
            customer_id=customer_id,
            deal_id=deal_id,
            personal=personal,
            date_from=date_from,
            date_to=date_to,
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
        Tạo mới hoạt động (S6-05).
        Xác thực quyền xem khách hàng / deal trước và luôn gán user_id = user.id.
        """
        if dto.customerId:
            CustomerRepository.get_scoped_by_id(db, dto.customerId, user)
        if dto.dealId:
            DealRepository.get_scoped_by_id(db, dto.dealId, user)

        new_activity = Activity(
            id=str(uuid.uuid4()),
            customer_id=dto.customerId,
            deal_id=dto.dealId,
            user_id=user.id,
            type=dto.type,
            title=dto.title,
            description=dto.description or "",
            notes=dto.notes or "",
        )
        return ActivityRepository.create(db, new_activity)
