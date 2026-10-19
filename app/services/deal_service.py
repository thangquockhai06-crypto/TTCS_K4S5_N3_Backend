import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update, false
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.scope import DataScope, get_user_data_scope
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.deal import Deal, deal_products
from app.models.deal_member import DealMember
from app.models.deal_outcome_history import DealOutcomeHistory
from app.models.saved_deal_filter import SavedDealFilter
from app.models.team import Team
from app.models.user import User
from app.models.win_loss import Competitor, WinLossReason
from app.repositories.deal_repository import DealRepository
from app.schemas.deal import CloseDealDTO, CreateDealDTO, ReopenDealDTO, UpdateDealDTO
from app.schemas.deal_filter import (
    DealFilterPaginatedResponse,
    DealFilterParams,
    DealResponseSchema,
)


def _get_team_member_ids(db: Session, user: User) -> List[str]:
    """Lấy danh sách tất cả ID người dùng thuộc phạm vi quản lý của Team Leader."""
    member_ids = {user.id}
    if user.team_id:
        same_team_users = db.query(User.id).filter(User.team_id == user.team_id).all()
        for (u_id,) in same_team_users:
            member_ids.add(u_id)
    led_teams = db.query(Team).filter(Team.leader_id == user.id).all()
    for t in led_teams:
        team_users = db.query(User.id).filter(User.team_id == t.id).all()
        for (u_id,) in team_users:
            member_ids.add(u_id)
        for u in t.users:
            member_ids.add(u.id)
    for t in user.teams:
        for u in t.users:
            member_ids.add(u.id)
    return list(member_ids)


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
    def filter_deals(
        db: Session,
        user: User,
        params: DealFilterParams,
    ) -> DealFilterPaginatedResponse:
        """
        Tìm kiếm toàn văn & lọc Cơ hội theo đa tiêu chí, kết hợp phân quyền sở hữu dữ liệu (SCRUM-206).
        """
        # 1. Kế thừa tiêu chí từ Saved Filter nếu có truyền saved_filter_id
        if params.saved_filter_id:
            saved = (
                db.query(SavedDealFilter)
                .filter(
                    SavedDealFilter.id == params.saved_filter_id,
                    SavedDealFilter.user_id == user.id,
                )
                .first()
            )
            if not saved:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy bộ lọc cá nhân đã lưu.",
                )
            crit = saved.filter_criteria or {}
            if params.search is None and "search" in crit:
                params.search = crit["search"]
            if params.stages is None and "stages" in crit:
                params.stages = crit["stages"]
            if params.min_amount is None and "min_amount" in crit:
                params.min_amount = Decimal(str(crit["min_amount"]))
            if params.max_amount is None and "max_amount" in crit:
                params.max_amount = Decimal(str(crit["max_amount"]))
            if params.expected_close_from is None and "expected_close_from" in crit:
                params.expected_close_from = (
                    date.fromisoformat(crit["expected_close_from"])
                    if isinstance(crit["expected_close_from"], str)
                    else crit["expected_close_from"]
                )
            if params.expected_close_to is None and "expected_close_to" in crit:
                params.expected_close_to = (
                    date.fromisoformat(crit["expected_close_to"])
                    if isinstance(crit["expected_close_to"], str)
                    else crit["expected_close_to"]
                )
            if params.product_id is None and "product_id" in crit:
                params.product_id = crit["product_id"]
            if params.product_ids is None and "product_ids" in crit:
                params.product_ids = crit["product_ids"]
            if params.owner_id is None and "owner_id" in crit:
                params.owner_id = crit["owner_id"]
            if params.sort_by == "expected_close_date" and "sort_by" in crit:
                params.sort_by = crit["sort_by"]
            if params.sort_order == "asc" and "sort_order" in crit:
                params.sort_order = crit["sort_order"]

        # 2. Phân quyền phạm vi dữ liệu sở hữu (Record-level Security)
        scope = get_user_data_scope(user)
        query = db.query(Deal)

        req_owner_id = params.owner_id or params.assigned_to

        if scope == DataScope.OWN:
            # SALES_REP: Được phép tìm kiếm và xem danh sách cơ hội do chính mình phụ trách hoặc tham gia phối hợp
            if req_owner_id:
                query = query.filter(
                    Deal.owner_id == req_owner_id,
                    or_(
                        Deal.owner_id == user.id,
                        Deal.members.any(DealMember.user_id == user.id),
                    ),
                )
            else:
                query = query.filter(
                    or_(
                        Deal.owner_id == user.id,
                        Deal.members.any(DealMember.user_id == user.id),
                    )
                )
        elif scope == DataScope.TEAM:
            # TEAM_LEAD: Xem và lọc được toàn bộ cơ hội thuộc phạm vi các nhân viên trong nhóm mình quản lý
            team_member_ids = _get_team_member_ids(db, user)
            if req_owner_id:
                if req_owner_id in team_member_ids:
                    query = query.filter(Deal.owner_id == req_owner_id)
                else:
                    # Yêu cầu xem user ngoài nhóm -> fail closed (không có quyền xem)
                    query = query.filter(false())
            else:
                query = query.filter(
                    or_(
                        Deal.owner_id.in_(team_member_ids),
                        Deal.members.any(DealMember.user_id.in_(team_member_ids)),
                    )
                )
        else:
            # DIRECTOR / ADMIN: Toàn quyền lọc và xem toàn bộ cơ hội trên toàn hệ thống
            if req_owner_id:
                query = query.filter(Deal.owner_id == req_owner_id)

        # 3. Áp dụng các điều kiện lọc linh hoạt (AND logic)
        # 3.1 Từ khóa tìm kiếm: search (LIKE trên title, mã deal id, customer full_name / company)
        if params.search and params.search.strip():
            search_term = f"%{params.search.strip()}%"
            query = query.outerjoin(Customer, Deal.customer_id == Customer.id).filter(
                or_(
                    Deal.title.ilike(search_term),
                    Deal.id.ilike(search_term),
                    Customer.full_name.ilike(search_term),
                    Customer.company.ilike(search_term),
                )
            )

        # 3.2 Giai đoạn Pipeline: stages (hỗ trợ lọc 1 hoặc nhiều giai đoạn)
        if params.stages:
            normalized_stages = [s.strip().lower() for s in params.stages if s.strip()]
            if normalized_stages:
                query = query.filter(Deal.stage.in_(normalized_stages))

        # 3.3 Khoảng giá trị cơ hội: min_amount & max_amount
        if params.min_amount is not None:
            query = query.filter(Deal.value >= params.min_amount)
        if params.max_amount is not None:
            query = query.filter(Deal.value <= params.max_amount)

        # 3.4 Khoảng ngày chốt dự kiến: expected_close_from & expected_close_to
        if params.expected_close_from is not None:
            query = query.filter(Deal.expected_close_date >= params.expected_close_from)
        if params.expected_close_to is not None:
            query = query.filter(Deal.expected_close_date <= params.expected_close_to)

        # 3.5 Sản phẩm / Dịch vụ: product_id hoặc product_ids
        p_ids = []
        if params.product_id:
            p_ids.append(params.product_id.strip())
        if params.product_ids:
            p_ids.extend([p.strip() for p in params.product_ids if p.strip()])
        p_ids = list(dict.fromkeys(p_ids))
        if p_ids:
            query = query.filter(
                Deal.id.in_(
                    select(deal_products.c.deal_id).where(deal_products.c.product_id.in_(p_ids))
                )
            )

        # 4. Tính tổng số lượng bản ghi (COUNT) và tổng giá trị (SUM(amount)) trong một câu truy vấn
        count_and_sum = query.with_entities(
            func.count(Deal.id),
            func.coalesce(func.sum(Deal.value), 0),
        ).first()

        total_items = int(count_and_sum[0]) if count_and_sum and count_and_sum[0] is not None else 0
        total_amount_sum = (
            Decimal(str(count_and_sum[1])) if count_and_sum and count_and_sum[1] is not None else Decimal(0)
        )

        page = max(1, params.page)
        page_size = max(1, min(100, params.page_size))
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

        # 5. Sắp xếp (ORDER BY)
        sort_col_map = {
            "expected_close_date": Deal.expected_close_date,
            "amount": Deal.value,
            "value": Deal.value,
            "created_at": Deal.created_at,
            "title": Deal.title,
            "stage": Deal.stage,
        }
        sort_attr = sort_col_map.get(params.sort_by or "expected_close_date", Deal.expected_close_date)

        if params.sort_order == "desc":
            order_expr = sort_attr.desc()
        else:
            order_expr = sort_attr.asc()

        query = query.order_by(order_expr, Deal.created_at.desc(), Deal.id.asc())

        # 6. Phân trang & joinedload nạp thông tin customer, owner (tránh N+1)
        offset = (page - 1) * page_size
        query = query.options(joinedload(Deal.customer), joinedload(Deal.owner))
        deals = query.offset(offset).limit(page_size).all()

        items = [
            DealResponseSchema(
                id=d.id,
                title=d.title,
                amount=d.value,
                value=d.value,
                stage=d.stage,
                probability=d.probability,
                customer_id=d.customer_id,
                customer_name=d.customer.full_name if d.customer else None,
                owner_id=d.owner_id,
                owner_name=d.owner.full_name if d.owner else None,
                expected_close_date=d.expected_close_date,
                status=d.status,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in deals
        ]

        return DealFilterPaginatedResponse(
            total_items=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_amount_sum=total_amount_sum,
            items=items,
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
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Thành viên phối hợp hoặc người dùng không có quyền quản lý không được phép thay đổi người sở hữu cơ hội.",
                )
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
