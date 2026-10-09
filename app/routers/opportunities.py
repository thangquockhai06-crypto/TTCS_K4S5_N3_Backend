from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.export import export_to_excel
from app.database import get_db
from app.dependencies import get_current_user
from app.models.deal import Deal
from app.models.user import User
from app.schemas.deal import (
    CloseDealDTO,
    CompetitorSummaryDTO,
    CreateDealDTO,
    DealDTO,
    DealOutcomeHistoryDTO,
    LostReasonSummaryDTO,
    MoveDealStageDTO,
    ReopenDealDTO,
    UpdateDealDTO,
)
from app.services.deal_service import DealService
router = APIRouter(prefix="/opportunities", tags=["Opportunities Management"])

def _to_deal_dto(deal: Deal, include_history: bool = True) -> DealDTO:


    return DealDTO(
        id=deal.id,
        title=deal.title,
        value=float(deal.value),
        stage=deal.stage,
        probability=deal.probability,
        customerId=deal.customer_id,
        ownerId=deal.owner_id,
        expectedCloseDate=deal.expected_close_date.isoformat() if deal.expected_close_date else None,
        createdAt=deal.created_at.isoformat() if deal.created_at else None,
        outcome=deal.status,
        status=deal.status,
        closedAt=deal.closed_at.isoformat() if deal.closed_at else None,
        closedBy=deal.closed_by,
        actualValue=deal.actual_value,
        signedDate=deal.signed_date.isoformat() if deal.signed_date else None,
        lostReasonId=deal.lost_reason_id,
        lostReason=(LostReasonSummaryDTO.model_validate(deal.lost_reason) if deal.lost_reason else None),
        lostReasonNote=deal.lost_reason_note,
        competitorId=deal.competitor_id,
        competitor=(CompetitorSummaryDTO.model_validate(deal.competitor) if deal.competitor else None),
        reopenedAt=deal.reopened_at.isoformat() if deal.reopened_at else None,
        reopenedBy=deal.reopened_by,
        reopenReason=deal.reopen_reason,
        history=(
            [DealOutcomeHistoryDTO.model_validate(item) for item in deal.outcome_history]
            if include_history
            else []
        ),
    )


def _validate_outcome(outcome: Optional[str]) -> Optional[str]:
    if outcome and outcome.upper() not in {"OPEN", "WON", "LOST", "ALL"}:
        raise HTTPException(status_code=400, detail="outcome must be OPEN, WON, LOST, or ALL.")
    return outcome.upper() if outcome else None


@router.get("", response_model=List[DealDTO], summary="List opportunities")
def get_opportunities(
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    closedFrom: Optional[date] = Query(None),
    closedTo: Optional[date] = Query(None),
    signedFrom: Optional[date] = Query(None),
    signedTo: Optional[date] = Query(None),
    lostReasonId: Optional[str] = Query(None),
    # Snake-case aliases keep the API usable by existing backend clients.
    closed_from: Optional[date] = Query(None, include_in_schema=False),
    closed_to: Optional[date] = Query(None, include_in_schema=False),
    signed_from: Optional[date] = Query(None, include_in_schema=False),
    signed_to: Optional[date] = Query(None, include_in_schema=False),
    lost_reason_id: Optional[str] = Query(None, include_in_schema=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DealDTO]:
    deals = DealService.get_deals(
        db=db,
        user=current_user,
        search=search,
        stage=stage,
        outcome=_validate_outcome(outcome),
        closed_from=closedFrom or closed_from,
        closed_to=closedTo or closed_to,
        signed_from=signedFrom or signed_from,
        signed_to=signedTo or signed_to,
        lost_reason_id=lostReasonId or lost_reason_id,
    )
    return [_to_deal_dto(deal, include_history=False) for deal in deals]


@router.get("/export", summary="Export opportunities")
def export_opportunities(
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
    headers = [
        "Opportunity ID",
        "Title",
        "Value",
        "Stage",
        "Outcome",
        "Actual value",
        "Signed date",
        "Lost reason",
        "Competitor",
        "Owner",
    ]
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
        sheet_title="Opportunities",
        headers=headers,
        rows=rows,
        filename="danh_sach_opportunities.xlsx",
    )


@router.post("", response_model=DealDTO, status_code=status.HTTP_201_CREATED, summary="Create opportunity")
def create_opportunity(
    dto: CreateDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    return _to_deal_dto(DealService.create_deal(db=db, dto=dto, user=current_user))


@router.get("/{opportunity_id}/history", response_model=List[DealOutcomeHistoryDTO], summary="Opportunity close/reopen history")
def get_opportunity_history(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DealOutcomeHistoryDTO]:
    deal = DealService.get_deal_by_id(db=db, deal_id=opportunity_id, user=current_user)
    return [DealOutcomeHistoryDTO.model_validate(item) for item in deal.outcome_history]


@router.post("/{opportunity_id}/close", response_model=DealDTO, summary="Close opportunity")
def close_opportunity(
    opportunity_id: str,
    dto: CloseDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    return _to_deal_dto(DealService.close_deal(db=db, deal_id=opportunity_id, dto=dto, user=current_user))


@router.post("/{opportunity_id}/reopen", response_model=DealDTO, summary="Reopen opportunity")
def reopen_opportunity(
    opportunity_id: str,
    dto: ReopenDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    return _to_deal_dto(DealService.reopen_deal(db=db, deal_id=opportunity_id, dto=dto, user=current_user))


@router.get("/{opportunity_id}", response_model=DealDTO, summary="Get opportunity")
def get_opportunity_detail(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    return _to_deal_dto(DealService.get_deal_by_id(db=db, deal_id=opportunity_id, user=current_user))


@router.patch("/{opportunity_id}", response_model=DealDTO, summary="Update opportunity")
def update_opportunity(
    opportunity_id: str,
    dto: UpdateDealDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    return _to_deal_dto(DealService.update_deal(db=db, deal_id=opportunity_id, dto=dto, user=current_user))


@router.patch("/{opportunity_id}/stage", response_model=DealDTO, summary="Move opportunity stage")
def move_opportunity_stage(
    opportunity_id: str,
    dto: MoveDealStageDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    deal = DealService.move_stage(db=db, deal_id=opportunity_id, new_stage=dto.stage, user=current_user)
    if deal is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cơ hội bán hàng.")
    return _to_deal_dto(deal)
