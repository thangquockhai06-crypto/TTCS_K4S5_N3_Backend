from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.export import export_to_excel
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.routers.opportunities import _to_deal_dto, _validate_outcome
from app.schemas.deal import (
    CloseDealDTO,
    CreateDealDTO,
    DealDTO,
    DealOutcomeHistoryDTO,
    MoveDealStageDTO,
    ReopenDealDTO,
    UpdateDealDTO,
)
from app.services.deal_service import DealService

router = APIRouter(prefix="/deals", tags=["Deals Pipeline (Kanban)"])


@router.get("", response_model=List[DealDTO], summary="List deals")
def get_deals(
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    closedFrom: Optional[date] = Query(None),
    closedTo: Optional[date] = Query(None),
    signedFrom: Optional[date] = Query(None),
    signedTo: Optional[date] = Query(None),
    lostReasonId: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DealDTO]:
    deals = DealService.get_deals(
        db=db,
        user=current_user,
        search=search,
        stage=stage,
        outcome=_validate_outcome(outcome),
        closed_from=closedFrom,
        closed_to=closedTo,
        signed_from=signedFrom,
        signed_to=signedTo,
        lost_reason_id=lostReasonId,
    )
    return [_to_deal_dto(deal, include_history=False) for deal in deals]


@router.get("/export", summary="Export deals")
def export_deals(
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deals = DealService.get_deals_for_export(
        db=db,
        user=current_user,
        search=search,
        stage=stage,
        outcome=_validate_outcome(outcome),
    )
    rows = [
        [
            deal.id,
            deal.title,
            float(deal.value),
            deal.stage,
            deal.status,
            float(deal.actual_value) if deal.actual_value is not None else "",
            deal.signed_date.isoformat() if deal.signed_date else "",
            deal.lost_reason.reason if deal.lost_reason else "",
            deal.competitor.name if deal.competitor else "",
            deal.owner_id,
        ]
        for deal in deals
    ]
    return export_to_excel(
        sheet_title="Deals",
        headers=["Deal ID", "Title", "Value", "Stage", "Outcome", "Actual value", "Signed date", "Lost reason", "Competitor", "Owner"],
        rows=rows,
        filename="danh_sach_deals.xlsx",
    )


@router.post("", response_model=DealDTO, status_code=status.HTTP_201_CREATED, summary="Create deal")
def create_deal(
    dto: CreateDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    return _to_deal_dto(DealService.create_deal(db=db, dto=dto, user=current_user))


@router.get("/{deal_id}/history", response_model=List[DealOutcomeHistoryDTO], summary="Deal close/reopen history")
def get_deal_history(
    deal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DealOutcomeHistoryDTO]:
    deal = DealService.get_deal_by_id(db=db, deal_id=deal_id, user=current_user)
    return [DealOutcomeHistoryDTO.model_validate(item) for item in deal.outcome_history]


@router.post("/{deal_id}/close", response_model=DealDTO, summary="Close deal")
def close_deal(
    deal_id: str,
    dto: CloseDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    return _to_deal_dto(DealService.close_deal(db=db, deal_id=deal_id, dto=dto, user=current_user))


@router.post("/{deal_id}/reopen", response_model=DealDTO, summary="Reopen deal")
def reopen_deal(
    deal_id: str,
    dto: ReopenDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    return _to_deal_dto(DealService.reopen_deal(db=db, deal_id=deal_id, dto=dto, user=current_user))


@router.get("/{deal_id}", response_model=DealDTO, summary="Get deal")
def get_deal_detail(
    deal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    return _to_deal_dto(DealService.get_deal_by_id(db=db, deal_id=deal_id, user=current_user))


@router.patch("/{deal_id}", response_model=DealDTO, summary="Update deal")
def update_deal(
    deal_id: str,
    dto: UpdateDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    return _to_deal_dto(DealService.update_deal(db=db, deal_id=deal_id, dto=dto, user=current_user))


@router.patch("/{deal_id}/stage", response_model=DealDTO, summary="Move deal stage")
def move_stage(
    deal_id: str,
    dto: MoveDealStageDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    deal = DealService.move_stage(db=db, deal_id=deal_id, new_stage=dto.stage, user=current_user)
    if deal is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cơ hội bán hàng.")
    return _to_deal_dto(deal)
