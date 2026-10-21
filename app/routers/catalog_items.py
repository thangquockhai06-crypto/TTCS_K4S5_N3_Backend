from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.catalog_item import CatalogItemCreateDTO, CatalogItemDTO, CatalogItemUpdateDTO
from app.services.catalog_item_service import CatalogItemService


router = APIRouter(prefix="/catalog-items", tags=["Catalog & Price Book"])


@router.get("", response_model=List[CatalogItemDTO], response_model_exclude_none=True)
def list_catalog_items(
    search: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    sort: str = Query("code"),
    descending: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CatalogItemDTO]:
    items, _ = CatalogItemService(db).list_items(
        user=current_user,
        search=search,
        item_type=type,
        item_status=status_filter,
        sort=sort,
        descending=descending,
        skip=skip,
        limit=limit,
    )
    return items


@router.post("", response_model=CatalogItemDTO, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
def create_catalog_item(
    dto: CatalogItemCreateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogItemDTO:
    return CatalogItemService(db).create_item(dto, current_user)


@router.get("/{item_id}", response_model=CatalogItemDTO, response_model_exclude_none=True)
def get_catalog_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogItemDTO:
    return CatalogItemService(db).get_item(item_id, current_user)


@router.put("/{item_id}", response_model=CatalogItemDTO, response_model_exclude_none=True)
def update_catalog_item(
    item_id: str,
    dto: CatalogItemUpdateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogItemDTO:
    return CatalogItemService(db).update_item(item_id, dto, current_user)


@router.delete("/{item_id}")
def delete_catalog_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    CatalogItemService(db).delete_item(item_id, current_user)
    return {"message": "Đã xóa catalog item."}


@router.post("/{item_id}/discontinue", response_model=CatalogItemDTO, response_model_exclude_none=True)
def discontinue_catalog_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogItemDTO:
    return CatalogItemService(db).discontinue(item_id, current_user)


@router.post("/{item_id}/reactivate", response_model=CatalogItemDTO, response_model_exclude_none=True)
def reactivate_catalog_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogItemDTO:
    return CatalogItemService(db).discontinue(item_id, current_user, reactivate=True)
