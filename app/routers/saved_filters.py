from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.saved_filter import SavedFilterPreset
from app.schemas.saved_filter import (
    SavedFilterPresetDTO,
    CreateSavedFilterDTO,
)
from app.services.saved_filter_service import SavedFilterService

router = APIRouter(prefix="/customer-filters", tags=["Saved Customer Filters (S3-07)"])


def _to_preset_dto(p: SavedFilterPreset) -> SavedFilterPresetDTO:
    return SavedFilterPresetDTO(
        id=p.id,
        userId=p.user_id,
        name=p.name,
        entityType=p.entity_type,
        filterCriteria=p.filter_criteria,
        isDefault=bool(p.is_default),
        createdAt=p.created_at.isoformat() if p.created_at else None,
    )


@router.get("", response_model=List[SavedFilterPresetDTO], summary="Lấy danh sách các bộ lọc đã lưu của người dùng hiện tại")
def get_saved_filters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SavedFilterPresetDTO]:
    presets = SavedFilterService.get_user_filters(
        db=db,
        user=current_user,
        entity_type="customer",
    )
    return [_to_preset_dto(p) for p in presets]


@router.post("", response_model=SavedFilterPresetDTO, status_code=status.HTTP_201_CREATED, summary="Lưu bộ lọc tùy chỉnh mới")
def create_saved_filter(
    dto: CreateSavedFilterDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedFilterPresetDTO:
    preset = SavedFilterService.create_filter(
        db=db,
        user=current_user,
        dto=dto,
    )
    return _to_preset_dto(preset)


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa bộ lọc đã lưu")
def delete_saved_filter(
    preset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    SavedFilterService.delete_filter(
        db=db,
        user=current_user,
        preset_id=preset_id,
    )
    return None
