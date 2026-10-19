import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.customer_search import normalize_text
from app.models.saved_deal_filter import SavedDealFilter
from app.models.user import User
from app.schemas.deal_filter import (
    SavedDealFilterCreate,
    SavedDealFilterResponse,
    SavedDealFilterUpdate,
)


class SavedFilterService:
    """Quản lý các bộ lọc cá nhân hay dùng cho Cơ hội bán hàng (SCRUM-206)."""

    def __init__(self, db: Session):
        self.db = db

    def list_saved_deal_filters(self, user: User) -> List[SavedDealFilterResponse]:
        """Lấy danh sách tất cả bộ lọc đã lưu của chính current_user."""
        filters = (
            self.db.query(SavedDealFilter)
            .filter(SavedDealFilter.user_id == user.id)
            .order_by(SavedDealFilter.is_default.desc(), SavedDealFilter.created_at.desc())
            .all()
        )
        return [
            SavedDealFilterResponse(
                id=f.id,
                name=f.name,
                filter_criteria=f.filter_criteria or {},
                is_default=bool(f.is_default),
                created_at=f.created_at,
                updated_at=f.updated_at,
            )
            for f in filters
        ]

    def get_saved_deal_filter(self, filter_id: str, user: User) -> SavedDealFilterResponse:
        """Lấy chi tiết một bộ lọc theo ID (chỉ chủ sở hữu)."""
        item = self._get_scoped_filter(filter_id, user)
        return SavedDealFilterResponse(
            id=item.id,
            name=item.name,
            filter_criteria=item.filter_criteria or {},
            is_default=bool(item.is_default),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def create_saved_deal_filter(
        self, dto: SavedDealFilterCreate, user: User
    ) -> SavedDealFilterResponse:
        """Tạo mới bộ lọc cá nhân. Nếu is_default=True, reset các filter khác về False."""
        self._ensure_unique_name(user=user, name=dto.name)

        if dto.is_default:
            self.db.query(SavedDealFilter).filter(
                SavedDealFilter.user_id == user.id
            ).update({SavedDealFilter.is_default: False})

        new_filter = SavedDealFilter(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=dto.name.strip(),
            filter_criteria=dto.filter_criteria,
            is_default=bool(dto.is_default),
        )
        self.db.add(new_filter)
        self.db.commit()
        self.db.refresh(new_filter)
        return SavedDealFilterResponse(
            id=new_filter.id,
            name=new_filter.name,
            filter_criteria=new_filter.filter_criteria or {},
            is_default=bool(new_filter.is_default),
            created_at=new_filter.created_at,
            updated_at=new_filter.updated_at,
        )

    def update_saved_deal_filter(
        self, filter_id: str, dto: SavedDealFilterUpdate, user: User
    ) -> SavedDealFilterResponse:
        """Sửa tên, tiêu chí hoặc cờ mặc định. Đảm bảo user chỉ được sửa filter của mình."""
        item = self._get_scoped_filter(filter_id, user)

        if dto.name is not None:
            self._ensure_unique_name(user=user, name=dto.name, exclude_id=item.id)
            item.name = dto.name.strip()

        if dto.filter_criteria is not None:
            item.filter_criteria = dto.filter_criteria

        if dto.is_default is True:
            self.db.query(SavedDealFilter).filter(
                SavedDealFilter.user_id == user.id,
                SavedDealFilter.id != item.id,
            ).update({SavedDealFilter.is_default: False})
            item.is_default = True
        elif dto.is_default is False:
            item.is_default = False

        self.db.commit()
        self.db.refresh(item)
        return SavedDealFilterResponse(
            id=item.id,
            name=item.name,
            filter_criteria=item.filter_criteria or {},
            is_default=bool(item.is_default),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def delete_saved_deal_filter(self, filter_id: str, user: User) -> None:
        """Xóa bộ lọc cá nhân (chỉ chủ sở hữu có quyền xóa)."""
        item = self._get_scoped_filter(filter_id, user)
        self.db.delete(item)
        self.db.commit()

    def _get_scoped_filter(self, filter_id: str, user: User) -> SavedDealFilter:
        """Kiểm tra sự tồn tại và quyền sở hữu của bộ lọc cá nhân."""
        # Kiểm tra tồn tại không phân biệt user để báo 403 nếu tồn tại nhưng không thuộc quyền sở hữu
        unscoped = self.db.query(SavedDealFilter).filter(SavedDealFilter.id == filter_id).first()
        if not unscoped:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy bộ lọc cá nhân.",
            )
        if unscoped.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập hoặc chỉnh sửa bộ lọc này.",
            )
        return unscoped

    def _ensure_unique_name(self, user: User, name: str, exclude_id: Optional[str] = None) -> None:
        """Đảm bảo tên bộ lọc không bị trùng lặp đối với cùng một người dùng."""
        normalized = normalize_text(name)
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tên bộ lọc không được để trống.",
            )
        query = self.db.query(SavedDealFilter).filter(
            SavedDealFilter.user_id == user.id,
            func.lower(SavedDealFilter.name) == name.strip().lower(),
        )
        if exclude_id:
            query = query.filter(SavedDealFilter.id != exclude_id)
        if query.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tên bộ lọc '{name.strip()}' đã tồn tại trong danh sách của bạn.",
            )
