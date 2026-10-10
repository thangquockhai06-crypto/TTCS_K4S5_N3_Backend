"""
CampaignService: Tầng xử lý nghiệp vụ Quản lý Chiến dịch Tiếp thị (SCRUM-44 / Sprint 4).
Hỗ trợ:
- Tạo mới, cập nhật, lấy chi tiết và xóa an toàn chiến dịch.
- Truy vấn tổng hợp hiệu quả thời gian thực (total_leads, total_deals, won_deals_count, total_revenue, roi)
  sử dụng tối ưu Subquery + Outer Join để tránh N+1 Query.
- Bảo toàn dữ liệu: Xóa chiến dịch sẽ ngắt liên kết (SET NULL) trên Leads và Deals, không gây cascade mất dữ liệu.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import func, case, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.deal import Deal
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignMetricsResponse,
    CampaignDetailResponse,
    LeadSummaryDTO,
    DealSummaryDTO,
)


class CampaignService:
    @staticmethod
    def create_campaign(db: Session, request: CampaignCreateRequest, current_user: User) -> Campaign:
        """Khai báo chiến dịch tiếp thị mới."""
        campaign = Campaign(
            id=str(uuid.uuid4()),
            name=request.name.strip(),
            channel=request.channel.strip(),
            budget=request.budget,
            start_date=request.start_date,
            end_date=request.end_date,
            status=request.status or "ACTIVE",
            description=request.description.strip() if request.description else None,
            created_by=current_user.id,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def get_campaigns_with_metrics(
        db: Session,
        status_filter: Optional[str] = None,
        channel: Optional[str] = None,
        search: Optional[str] = None,
        start_date_from: Optional[date] = None,
        end_date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[CampaignMetricsResponse], int]:
        """
        Truy vấn danh sách chiến dịch kèm các chỉ số thống kê tổng hợp hiệu quả:
        Sử dụng Subquery + Outer Join để gom nhóm và tính toán trong một lần truy vấn SQL duy nhất.
        """
        # 1. Subquery đếm số lead phát sinh từ chiến dịch
        lead_subq = (
            db.query(
                Lead.campaign_id.label("campaign_id"),
                func.count(Lead.id).label("total_leads"),
            )
            .filter(Lead.campaign_id.isnot(None))
            .group_by(Lead.campaign_id)
            .subquery()
        )

        # 2. Subquery đếm số deal, số deal won và tổng doanh thu đã chốt
        won_revenue_case = case((func.lower(Deal.stage) == "won", Deal.value), else_=Decimal("0.00"))
        won_count_case = case((func.lower(Deal.stage) == "won", 1), else_=0)

        deal_subq = (
            db.query(
                Deal.campaign_id.label("campaign_id"),
                func.count(Deal.id).label("total_deals"),
                func.sum(won_count_case).label("won_deals_count"),
                func.sum(won_revenue_case).label("total_revenue"),
            )
            .filter(Deal.campaign_id.isnot(None))
            .group_by(Deal.campaign_id)
            .subquery()
        )

        # 3. Main Query: Join Campaign với 2 subqueries
        query = (
            db.query(
                Campaign,
                func.coalesce(lead_subq.c.total_leads, 0).label("total_leads"),
                func.coalesce(deal_subq.c.total_deals, 0).label("total_deals"),
                func.coalesce(deal_subq.c.won_deals_count, 0).label("won_deals_count"),
                func.coalesce(deal_subq.c.total_revenue, Decimal("0.00")).label("total_revenue"),
            )
            .outerjoin(lead_subq, Campaign.id == lead_subq.c.campaign_id)
            .outerjoin(deal_subq, Campaign.id == deal_subq.c.campaign_id)
        )

        # 4. Áp dụng các bộ lọc (Filters)
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                (Campaign.name.ilike(s)) | (Campaign.description.ilike(s))
            )
        if status_filter:
            query = query.filter(Campaign.status == status_filter.strip().upper())
        if channel:
            query = query.filter(Campaign.channel.ilike(f"%{channel.strip()}%"))
        if start_date_from:
            query = query.filter(Campaign.start_date >= start_date_from)
        if end_date_to:
            query = query.filter(Campaign.end_date <= end_date_to)

        total_count = query.count()

        results = (
            query.order_by(Campaign.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        items: List[CampaignMetricsResponse] = []
        for camp, total_leads, total_deals, won_deals_count, total_revenue in results:
            budget = Decimal(str(camp.budget or 0))
            revenue = Decimal(str(total_revenue or 0))
            profit = revenue - budget

            roi: Optional[float] = None
            if budget > Decimal("0.00"):
                roi = round(float((revenue - budget) / budget * 100), 2)

            items.append(
                CampaignMetricsResponse(
                    id=camp.id,
                    name=camp.name,
                    channel=camp.channel,
                    budget=budget,
                    start_date=camp.start_date,
                    end_date=camp.end_date,
                    status=camp.status,
                    description=camp.description,
                    created_by=camp.created_by,
                    created_at=camp.created_at,
                    updated_at=camp.updated_at,
                    total_leads=int(total_leads or 0),
                    total_deals=int(total_deals or 0),
                    won_deals_count=int(won_deals_count or 0),
                    total_revenue=revenue,
                    roi=roi,
                    profit=profit,
                )
            )

        return items, total_count

    @staticmethod
    def get_campaign_detail(db: Session, campaign_id: str) -> CampaignDetailResponse:
        """Chi tiết một chiến dịch kèm danh sách các lead và deal phát sinh."""
        camp = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not camp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy chiến dịch tiếp thị.",
            )

        # Lấy danh sách leads thuộc chiến dịch
        leads = (
            db.query(Lead)
            .filter(Lead.campaign_id == campaign_id)
            .order_by(Lead.created_at.desc())
            .all()
        )

        # Lấy danh sách deals thuộc chiến dịch
        deals = (
            db.query(Deal)
            .filter(Deal.campaign_id == campaign_id)
            .order_by(Deal.created_at.desc())
            .all()
        )

        total_leads = len(leads)
        total_deals = len(deals)
        won_deals = [d for d in deals if (d.stage or "").lower() == "won"]
        won_deals_count = len(won_deals)
        total_revenue = sum((Decimal(str(d.value or 0)) for d in won_deals), Decimal("0.00"))

        budget = Decimal(str(camp.budget or 0))
        profit = total_revenue - budget
        roi: Optional[float] = None
        if budget > Decimal("0.00"):
            roi = round(float((total_revenue - budget) / budget * 100), 2)

        return CampaignDetailResponse(
            id=camp.id,
            name=camp.name,
            channel=camp.channel,
            budget=budget,
            start_date=camp.start_date,
            end_date=camp.end_date,
            status=camp.status,
            description=camp.description,
            created_by=camp.created_by,
            created_at=camp.created_at,
            updated_at=camp.updated_at,
            total_leads=total_leads,
            total_deals=total_deals,
            won_deals_count=won_deals_count,
            total_revenue=total_revenue,
            roi=roi,
            profit=profit,
            leads=[LeadSummaryDTO.model_validate(l) for l in leads],
            deals=[DealSummaryDTO.model_validate(d) for d in deals],
        )

    @staticmethod
    def update_campaign(
        db: Session,
        campaign_id: str,
        request: CampaignUpdateRequest,
        current_user: User,
    ) -> Campaign:
        """Cập nhật thông tin chiến dịch."""
        camp = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not camp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy chiến dịch tiếp thị.",
            )

        new_start = request.start_date or camp.start_date
        new_end = request.end_date or camp.end_date
        if new_end < new_start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ngày kết thúc (end_date) phải lớn hơn hoặc bằng ngày bắt đầu (start_date).",
            )

        if request.name is not None:
            camp.name = request.name.strip()
        if request.channel is not None:
            camp.channel = request.channel.strip()
        if request.budget is not None:
            camp.budget = request.budget
        if request.start_date is not None:
            camp.start_date = request.start_date
        if request.end_date is not None:
            camp.end_date = request.end_date
        if request.status is not None:
            camp.status = request.status
        if request.description is not None:
            camp.description = request.description.strip() if request.description else None

        db.commit()
        db.refresh(camp)
        return camp

    @staticmethod
    def delete_campaign(db: Session, campaign_id: str, current_user: User) -> bool:
        """
        Xóa chiến dịch tiếp thị an toàn:
        Ngắt liên kết (SET NULL) trên Leads và Deals để không làm mất dữ liệu khách hàng.
        """
        camp = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not camp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy chiến dịch tiếp thị.",
            )

        # Ngắt liên kết an toàn trên leads và deals
        db.query(Lead).filter(Lead.campaign_id == campaign_id).update({"campaign_id": None})
        db.query(Deal).filter(Deal.campaign_id == campaign_id).update({"campaign_id": None})

        db.delete(camp)
        db.commit()
        return True
