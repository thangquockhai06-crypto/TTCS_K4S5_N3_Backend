from datetime import date
from decimal import Decimal
from typing import Any, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
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
from app.schemas.deal_filter import (
    DealFilterPaginatedResponse,
    DealFilterParams,
    SavedDealFilterCreate,
    SavedDealFilterResponse,
    SavedDealFilterUpdate,
)
from app.services.deal_service import DealService
from app.services.saved_filter_service import SavedFilterService

router = APIRouter(prefix="/deals", tags=["Deals Pipeline (Kanban)"])


# ==============================================================================
# 1. QUẢN LÝ BỘ LỌC CÁ NHÂN (SAVED FILTERS - SCRUM-206)
# ==============================================================================

@router.get("/saved-filters", response_model=List[SavedDealFilterResponse], summary="Lấy danh sách bộ lọc cơ hội đã lưu")
def list_saved_deal_filters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SavedDealFilterResponse]:
    return SavedFilterService(db).list_saved_deal_filters(user=current_user)


@router.post("/saved-filters", response_model=SavedDealFilterResponse, status_code=status.HTTP_201_CREATED, summary="Tạo mới bộ lọc cơ hội cá nhân")
def create_saved_deal_filter(
    dto: SavedDealFilterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedDealFilterResponse:
    return SavedFilterService(db).create_saved_deal_filter(dto=dto, user=current_user)


@router.get("/saved-filters/{filter_id}", response_model=SavedDealFilterResponse, summary="Xem chi tiết bộ lọc cơ hội đã lưu")
def get_saved_deal_filter(
    filter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedDealFilterResponse:
    return SavedFilterService(db).get_saved_deal_filter(filter_id=filter_id, user=current_user)


@router.put("/saved-filters/{filter_id}", response_model=SavedDealFilterResponse, summary="Cập nhật bộ lọc cơ hội cá nhân (PUT)")
def update_saved_deal_filter_put(
    filter_id: str,
    dto: SavedDealFilterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedDealFilterResponse:
    return SavedFilterService(db).update_saved_deal_filter(filter_id=filter_id, dto=dto, user=current_user)


@router.patch("/saved-filters/{filter_id}", response_model=SavedDealFilterResponse, summary="Cập nhật một phần bộ lọc cơ hội cá nhân (PATCH)")
def update_saved_deal_filter_patch(
    filter_id: str,
    dto: SavedDealFilterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedDealFilterResponse:
    return SavedFilterService(db).update_saved_deal_filter(filter_id=filter_id, dto=dto, user=current_user)


@router.delete("/saved-filters/{filter_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa bộ lọc cơ hội cá nhân")
def delete_saved_deal_filter(
    filter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    SavedFilterService(db).delete_saved_deal_filter(filter_id=filter_id, user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==============================================================================
# 2. TÌM KIẾM VÀ LỌC CƠ HỘI NÂNG CAO ĐA ĐIỀU KIỆN (SCRUM-206)
# ==============================================================================

@router.get("", summary="Tìm kiếm, lọc danh sách cơ hội đa tiêu chí (SCRUM-206)")
def get_deals(
    search: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo tên cơ hội, mã cơ hội, khách hàng"),
    stages: Optional[List[str]] = Query(None, description="Danh sách giai đoạn pipeline (ví dụ: stages=proposal&stages=negotiation)"),
    stage: Optional[str] = Query(None, description="Giai đoạn pipeline đơn lẻ"),
    min_amount: Optional[Decimal] = Query(None, alias="min_amount", ge=0, description="Khoảng giá trị tối thiểu"),
    max_amount: Optional[Decimal] = Query(None, alias="max_amount", ge=0, description="Khoảng giá trị tối đa"),
    expected_close_from: Optional[date] = Query(None, alias="expected_close_from", description="Ngày chốt dự kiến từ"),
    expected_close_to: Optional[date] = Query(None, alias="expected_close_to", description="Ngày chốt dự kiến đến"),
    product_id: Optional[str] = Query(None, alias="product_id", description="Lọc theo sản phẩm quan tâm"),
    product_ids: Optional[List[str]] = Query(None, alias="product_ids", description="Lọc theo nhiều sản phẩm"),
    owner_id: Optional[str] = Query(None, alias="owner_id", description="Người phụ trách cơ hội"),
    assigned_to: Optional[str] = Query(None, alias="assigned_to", description="Người phụ trách (alias)"),
    sort_by: Optional[str] = Query("expected_close_date", alias="sort_by", description="Sắp xếp theo: expected_close_date, amount, created_at"),
    sort_order: Optional[str] = Query("asc", alias="sort_order", description="Thứ tự: asc hoặc desc"),
    page: Optional[int] = Query(None, ge=1, description="Trang hiện tại (1-indexed)"),
    page_size: Optional[int] = Query(None, ge=1, le=100, alias="page_size", description="Số bản ghi trên mỗi trang"),
    saved_filter_id: Optional[str] = Query(None, alias="saved_filter_id", description="Áp dụng bộ lọc cá nhân đã lưu"),
    paginated: Optional[bool] = Query(None, description="Bắt buộc trả về định dạng phân trang DealFilterPaginatedResponse"),
    # Legacy query parameters
    outcome: Optional[str] = Query(None),
    closedFrom: Optional[date] = Query(None),
    closedTo: Optional[date] = Query(None),
    signedFrom: Optional[date] = Query(None),
    signedTo: Optional[date] = Query(None),
    lostReasonId: Optional[str] = Query(None),
    response: Response = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    is_paginated_request = (
        paginated is True
        or page is not None
        or page_size is not None
        or stages is not None
        or min_amount is not None
        or max_amount is not None
        or expected_close_from is not None
        or expected_close_to is not None
        or product_id is not None
        or product_ids is not None
        or saved_filter_id is not None
        or owner_id is not None
        or assigned_to is not None
        or (sort_by is not None and sort_by != "expected_close_date")
        or (sort_order is not None and sort_order.lower() != "asc")
    )

    if is_paginated_request:
        effective_stages = stages or []
        if stage and stage not in effective_stages:
            effective_stages = list(effective_stages) + [stage]

        params = DealFilterParams(
            search=search,
            stages=effective_stages if effective_stages else None,
            min_amount=min_amount,
            max_amount=max_amount,
            expected_close_from=expected_close_from,
            expected_close_to=expected_close_to,
            product_id=product_id,
            product_ids=product_ids,
            owner_id=owner_id or assigned_to,
            sort_by=sort_by or "expected_close_date",
            sort_order=sort_order or "asc",
            page=page or 1,
            page_size=page_size or 20,
            saved_filter_id=saved_filter_id,
        )
        return DealService.filter_deals(db=db, user=current_user, params=params)

    # Legacy fallback khi không truyền tham số phân trang mới
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
    if response is not None:
        response.headers["X-Total-Count"] = str(len(deals))
    return [_to_deal_dto(deal, include_history=False) for deal in deals]


@router.post("/search", response_model=DealFilterPaginatedResponse, summary="Tìm kiếm và lọc cơ hội qua HTTP POST (SCRUM-206)")
def search_deals_post(
    params: DealFilterParams,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealFilterPaginatedResponse:
    return DealService.filter_deals(db=db, user=current_user, params=params)


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
