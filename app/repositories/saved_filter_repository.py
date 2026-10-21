from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.saved_filter import SavedFilterPreset
from app.repositories.base_repository import BaseRepository


class SavedFilterRepository(BaseRepository):
    """
    Repository quản lý Bộ lọc tùy chỉnh đã lưu (Saved Filter Preset) S3-07.
    Bảo vệ cô lập: người dùng chỉ xem và thao tác trên bộ lọc do chính mình tạo.
    """

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: str,
        entity_type: str = "customer",
    ) -> List[SavedFilterPreset]:
        return (
            db.query(SavedFilterPreset)
            .filter(
                SavedFilterPreset.user_id == user_id,
                SavedFilterPreset.entity_type == entity_type,
            )
            .order_by(SavedFilterPreset.created_at.desc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, preset_id: str) -> Optional[SavedFilterPreset]:
        return db.query(SavedFilterPreset).filter(SavedFilterPreset.id == preset_id).first()

    @staticmethod
    def create(db: Session, preset: SavedFilterPreset) -> SavedFilterPreset:
        db.add(preset)
        db.commit()
        db.refresh(preset)
        return preset

    @staticmethod
    def delete(db: Session, preset: SavedFilterPreset) -> None:
        db.delete(preset)
        db.commit()
