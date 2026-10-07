import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.saved_filter import SavedFilterPreset
from app.models.user import User
from app.schemas.saved_filter import CreateSavedFilterDTO
from app.repositories.saved_filter_repository import SavedFilterRepository


class SavedFilterService:
    """
    Service quản lý Bộ lọc tùy chỉnh đã lưu (Saved Filter Preset) S3-07.
    Bảo vệ cô lập: Mỗi người dùng chỉ có quyền đọc/ghi trên các bộ lọc của riêng mình.
    """

    @staticmethod
    def get_user_filters(
        db: Session,
        user: User,
        entity_type: str = "customer",
    ) -> List[SavedFilterPreset]:
        return SavedFilterRepository.get_by_user(db, user_id=user.id, entity_type=entity_type)

    @staticmethod
    def create_filter(
        db: Session,
        user: User,
        dto: CreateSavedFilterDTO,
    ) -> SavedFilterPreset:
        new_preset = SavedFilterPreset(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=dto.name.strip(),
            entity_type=dto.entityType or "customer",
            filter_criteria=dto.filterCriteria,
            is_default=dto.isDefault or False,
        )
        return SavedFilterRepository.create(db, new_preset)

    @staticmethod
    def delete_filter(
        db: Session,
        user: User,
        preset_id: str,
    ) -> None:
        preset = SavedFilterRepository.get_by_id(db, preset_id)
        if not preset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cấu hình bộ lọc đã lưu.",
            )
        if preset.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xóa bộ lọc của người dùng khác.",
            )
        SavedFilterRepository.delete(db, preset)
