from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.customer_search import SavedFilterCreateDTO, SavedFilterDTO, SavedFilterUpdateDTO
from app.services.customer_search_service import CustomerSearchService

router = APIRouter(prefix="/saved-filters", tags=["Saved Customer Filters"])


@router.get("", response_model=List[SavedFilterDTO])
def list_saved_filters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SavedFilterDTO]:
    return CustomerSearchService(db).list_saved_filters(current_user)


@router.get("/{filter_id}", response_model=SavedFilterDTO)
def get_saved_filter(
    filter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedFilterDTO:
    return CustomerSearchService(db).get_saved_filter(filter_id, current_user)

@router.post("", response_model=SavedFilterDTO, status_code=status.HTTP_201_CREATED)
def create_saved_filter(
    dto: SavedFilterCreateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedFilterDTO:
    return CustomerSearchService(db).create_saved_filter(dto, current_user)


@router.patch("/{filter_id}", response_model=SavedFilterDTO)
def update_saved_filter(
    filter_id: str,
    dto: SavedFilterUpdateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedFilterDTO:
    return CustomerSearchService(db).update_saved_filter(filter_id, dto, current_user)


@router.delete("/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_filter(
    filter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    CustomerSearchService(db).delete_saved_filter(filter_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
