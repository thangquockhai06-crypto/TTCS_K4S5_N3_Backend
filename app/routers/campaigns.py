from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.campaign import CampaignDTO, CreateCampaignDTO, UpdateCampaignDTO
from app.services.campaign_service import CampaignService

router = APIRouter(prefix="/campaigns", tags=["Marketing Campaigns (EP-04: S4-03)"])


@router.get("", response_model=List[CampaignDTO], summary="Lấy danh sách chiến dịch tiếp thị kèm số liệu tổng hợp thực tế")
def get_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CampaignDTO]:
    """
    S4-03: Hiển thị danh sách chiến dịch tiếp thị kèm:
    - totalLeads: Số đầu mối phát sinh từ chiến dịch
    - totalDeals: Số cơ hội bán hàng liên kết
    - actualRevenue: Doanh thu thực tế chốt thắng (won) từ CSDL
    """
    return CampaignService.get_campaigns(db=db, skip=skip, limit=limit)


@router.get("/{campaign_id}", response_model=CampaignDTO, summary="Xem chi tiết chiến dịch tiếp thị")
def get_campaign_detail(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignDTO:
    return CampaignService.get_campaign_by_id(db=db, campaign_id=campaign_id)


@router.post("", response_model=CampaignDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới chiến dịch tiếp thị")
def create_campaign(
    dto: CreateCampaignDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignDTO:
    return CampaignService.create_campaign(db=db, dto=dto)
