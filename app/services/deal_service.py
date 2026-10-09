import json
import uuid
from datetime import date, datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.scope import DataScope, get_user_data_scope
from app.models.audit_log import AuditLog
from app.models.deal import Deal
from app.models.deal_outcome_history import DealOutcomeHistory
from app.models.user import User
from app.models.win_loss import Competitor, WinLossReason
from app.repositories.deal_repository import DealRepository
from app.schemas.deal import CloseDealDTO, CreateDealDTO, ReopenDealDTO, UpdateDealDTO


OPEN_STAGES = {"lead", "contact", "proposal", "negotiation"}
TEAM_LEAD_ROLES = {
    "team lead",
    "team leader",
    "sales leader",
    "sales manager",
    "manager",
    "lead",
    "revops lead",
    "trưởng nhóm",
    "trưởng phòng",
}
HIGHER_ROLES = {
    "super admin",
    "admin",
    "sales director",
    "director",
    "vp of sales",
    "giám đốc kinh doanh",
    "quản trị viên",
}


def _normalized_role(user: User) -> str:
    return (user.role or "").strip().lower().replace("_", " ")


def _as_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="expectedCloseDate must be a valid ISO date.") from exc


def _audit(
    db: Session,
    user: User,
    deal: Deal,
    action: str,
    details: dict,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id,
            performed_by=user.id,
            user_name=user.full_name,
            user_email=user.email,
            action=action,
            target_type="opportunity",
            target_id=deal.id,
            details=json.dumps(details, ensure_ascii=False, default=str),
        )
    )


class DealService:
    """Deal lifecycle and edit rules shared by both deal API surfaces."""

    @staticmethod
    def get_deals(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        stage: Optional[str] = None,
        outcome: Optional[str] = None,
        closed_from: Optional[date] = None,
        closed_to: Optional[date] = None,
        signed_from: Optional[date] = None,
        signed_to: Optional[date] = None,
        lost_reason_id: Optional[str] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Deal]:
        return DealRepository.get_all(
            db=db,
            user=user,
            search=search,
            stage=stage,
            outcome=outcome,
            closed_from=closed_from,
            closed_to=closed_to,
            signed_from=signed_from,
            signed_to=signed_to,
            lost_reason_id=lost_reason_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_deals_for_export(
        db: Session,
        user: User,
        search: Optional[str] = None,
        stage: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> List[Deal]:
        return DealRepository.get_all_for_export(
            db=db,
            user=user,
            search=search,
            stage=stage,
            outcome=outcome,
        )

    @staticmethod
    def get_deal_by_id(db: Session, deal_id: str, user: Optional[User] = None) -> Optional[Deal]:
        if user is not None:
            return DealRepository.get_scoped_by_id(db, deal_id, user)
        return DealRepository.get_by_id(db, deal_id)

    @staticmethod
    def create_deal(db: Session, dto: CreateDealDTO, user: User) -> Deal:
        stage = dto.stage.strip().lower()
        if stage not in OPEN_STAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Closed outcomes must be recorded through the close endpoint.",
            )
        new_deal = Deal(
            id=str(uuid.uuid4()),
            title=dto.title.strip(),
            value=dto.value,
            stage=stage,
            probability=dto.probability or 20,
            customer_id=dto.customerId,
            owner_id=user.id,
            expected_close_date=_as_date(dto.expectedCloseDate),
            status="OPEN",
            last_open_stage=stage,
        )
        return DealRepository.create(db, new_deal)

    @staticmethod
    def _scoped_for_update(db: Session, deal_id: str, user: User) -> Deal:
        DealRepository.get_scoped_by_id(db, deal_id, user)
        deal = DealRepository.get_for_update(db, deal_id)
        if deal is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy cơ hội bán hàng.")
        return deal

    @staticmethod
    def move_stage(db: Session, deal_id: str, new_stage: str, user: Optional[User] = None) -> Optional[Deal]:
        deal = DealRepository.get_scoped_by_id(db, deal_id, user) if user is not None else DealRepository.get_by_id(db, deal_id)
        if not deal:
            return None
        if deal.is_closed:
            raise HTTPException(status_code=409, detail="Closed opportunities cannot be edited. Reopen the opportunity first.")
        normalized_stage = new_stage.strip().lower()
        if normalized_stage not in OPEN_STAGES:
            raise HTTPException(
                status_code=400,
                detail="Use the close endpoint to set a WON or LOST outcome.",
            )
        deal.last_open_stage = normalized_stage
        return DealRepository.update_stage(db, deal, normalized_stage)

    @staticmethod
    def update_deal(db: Session, deal_id: str, dto: UpdateDealDTO, user: User) -> Deal:
        deal = DealRepository.get_scoped_by_id(db, deal_id, user)
        if deal.is_closed:
            raise HTTPException(status_code=409, detail="Closed opportunities cannot be edited. Reopen the opportunity first.")

        values = dto.model_dump(exclude_unset=True, by_alias=False)
        if "stage" in values and values["stage"] is not None:
            stage = values["stage"].strip().lower()
            if stage not in OPEN_STAGES:
                raise HTTPException(status_code=400, detail="Use the close endpoint to set a WON or LOST outcome.")
            deal.stage = stage
            deal.last_open_stage = stage
        if "title" in values and values["title"] is not None:
            deal.title = values["title"]
        if "value" in values and values["value"] is not None:
            deal.value = values["value"]
        if "probability" in values and values["probability"] is not None:
            deal.probability = values["probability"]
        if "customer_id" in values and values["customer_id"] is not None:
            deal.customer_id = values["customer_id"]
        if "expected_close_date" in values:
            deal.expected_close_date = values["expected_close_date"]
        if "owner_id" in values and values["owner_id"] is not None:
            if get_user_data_scope(user) != DataScope.ALL:
                raise HTTPException(status_code=403, detail="Only users with global deal-management scope can change ownership.")
            deal.owner_id = values["owner_id"]
        return DealRepository.update(db, deal)

    @staticmethod
    def close_deal(db: Session, deal_id: str, dto: CloseDealDTO, user: User) -> Deal:
        deal = DealService._scoped_for_update(db, deal_id, user)
        if deal.is_closed:
            raise HTTPException(status_code=409, detail="Opportunity is already closed.")
        if dto.signed_date and dto.signed_date > date.today():
            raise HTTPException(status_code=400, detail="signedDate cannot be in the future.")

        now = datetime.utcnow()
        previous_stage = deal.stage if deal.stage in OPEN_STAGES else "negotiation"
        lost_reason = None
        competitor = None
        if dto.outcome == "LOST":
            lost_reason = (
                db.query(WinLossReason)
                .filter(
                    WinLossReason.id == dto.lost_reason_id,
                    WinLossReason.result_type == "LOST",
                    WinLossReason.is_active.is_(True),
                )
                .first()
            )
            if lost_reason is None:
                raise HTTPException(status_code=400, detail="lostReasonId must reference an active LOST reason.")
            if lost_reason.code.upper() == "OTHER" and not (dto.lost_reason_note or "").strip():
                raise HTTPException(status_code=400, detail="lostReasonNote is required when the reason is OTHER.")
            if dto.competitor_id:
                competitor = (
                    db.query(Competitor)
                    .filter(Competitor.id == dto.competitor_id, Competitor.is_active.is_(True))
                    .first()
                )
                if competitor is None:
                    raise HTTPException(status_code=400, detail="competitorId must reference an active competitor.")
        elif dto.actual_value is None or dto.signed_date is None:
            raise HTTPException(status_code=400, detail="actualValue and signedDate are required when closing as WON.")

        actual_value = dto.actual_value if dto.outcome == "WON" else None
        signed_date = dto.signed_date if dto.outcome == "WON" else None
        lost_reason_id = lost_reason.id if lost_reason else None
        lost_reason_note = dto.lost_reason_note if dto.outcome == "LOST" else None
        competitor_id = competitor.id if competitor else None
        resulting_stage = "won" if dto.outcome == "WON" else "lost"

        result = db.execute(
            update(Deal)
            .where(Deal.id == deal.id, Deal.status == "OPEN")
            .values(
                status=dto.outcome,
                stage=resulting_stage,
                last_open_stage=previous_stage,
                closed_at=now,
                closed_by=user.id,
                actual_value=actual_value,
                signed_date=signed_date,
                lost_reason_id=lost_reason_id,
                lost_reason_note=lost_reason_note,
                competitor_id=competitor_id,
            )
        )
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail="Opportunity is already closed.")
        db.expire(deal)

        history = DealOutcomeHistory(
            deal_id=deal.id,
            action="CLOSED",
            outcome=dto.outcome,
            previous_status="OPEN",
            resulting_status=dto.outcome,
            previous_stage=previous_stage,
            resulting_stage=resulting_stage,
            actor_id=user.id,
            event_at=now,
            closed_at=now,
            closed_by=user.id,
            actual_value=actual_value,
            signed_date=signed_date,
            lost_reason_id=lost_reason_id,
            lost_reason_note=lost_reason_note,
            competitor_id=competitor_id,
        )
        db.add(history)
        if lost_reason:
            lost_reason.usage_count = (lost_reason.usage_count or 0) + 1
        _audit(
            db,
            user,
            deal,
            "OPPORTUNITY_CLOSED",
            {
                "previousStatus": "OPEN",
                "outcome": dto.outcome,
                "actualValue": deal.actual_value,
                "signedDate": deal.signed_date,
                "lostReasonId": deal.lost_reason_id,
                "lostReasonNote": deal.lost_reason_note,
                "competitorId": deal.competitor_id,
            },
        )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="Opportunity could not be closed because its state changed. Retry the request.") from exc
        db.refresh(deal)
        return deal

    @staticmethod
    def reopen_deal(db: Session, deal_id: str, dto: ReopenDealDTO, user: User) -> Deal:
        role = _normalized_role(user)
        if role not in TEAM_LEAD_ROLES and role not in HIGHER_ROLES:
            raise HTTPException(status_code=403, detail="Only a Team Lead or higher may reopen an opportunity.")

        deal = DealService._scoped_for_update(db, deal_id, user)
        if not deal.is_closed:
            raise HTTPException(status_code=409, detail="Opportunity is not closed.")

        now = datetime.utcnow()
        previous_status = deal.status
        previous_stage = deal.stage
        history = DealOutcomeHistory(
            deal_id=deal.id,
            action="REOPENED",
            outcome=previous_status,
            previous_status=previous_status,
            resulting_status="OPEN",
            previous_stage=previous_stage,
            resulting_stage=deal.last_open_stage or "negotiation",
            actor_id=user.id,
            event_at=now,
            closed_at=deal.closed_at,
            closed_by=deal.closed_by,
            actual_value=deal.actual_value,
            signed_date=deal.signed_date,
            lost_reason_id=deal.lost_reason_id,
            lost_reason_note=deal.lost_reason_note,
            competitor_id=deal.competitor_id,
            reopen_reason=dto.reopen_reason,
        )
        db.add(history)

        resulting_stage = deal.last_open_stage or "negotiation"
        result = db.execute(
            update(Deal)
            .where(Deal.id == deal.id, Deal.status == previous_status)
            .values(
                status="OPEN",
                stage=resulting_stage,
                closed_at=None,
                closed_by=None,
                actual_value=None,
                signed_date=None,
                lost_reason_id=None,
                lost_reason_note=None,
                competitor_id=None,
                reopened_at=now,
                reopened_by=user.id,
                reopen_reason=dto.reopen_reason,
            )
        )
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail="Opportunity is no longer closed.")
        db.expire(deal)
        _audit(
            db,
            user,
            deal,
            "OPPORTUNITY_REOPENED",
            {
                "previousStatus": previous_status,
                "previousStage": previous_stage,
                "resultingStage": deal.stage,
                "reopenReason": dto.reopen_reason,
            },
        )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="Opportunity could not be reopened because its state changed.") from exc
        db.refresh(deal)
        return deal
