import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.campaign import Campaign
from app.schemas.campaign import CreateCampaignDTO, UpdateCampaignDTO, CampaignDTO
from app.repositories.campaign_repository import CampaignRepository


class CampaignService:
    """
    Tầng Service quản lý Chiến dịch Tiếp thị & Đo lường Hiệu quả (EP-04: S4-03 Campaign Tracking).
    Tính toán số liệu dẫn xuất từ dữ liệu thật trong CSDL (leads count, deals count, actual revenue).
    """

    @staticmethod
    def get_campaigns(db: Session, skip: int = 0, limit: int = 100) -> List[CampaignDTO]:
        campaigns = CampaignRepository.get_all(db, skip=skip, limit=limit)
        results = []
        for c in campaigns:
            metrics = CampaignRepository.get_campaign_metrics(db, c.id)
            results.append(
                CampaignDTO(
                    id=c.id,
                    name=c.name,
                    code=c.code,
                    type=c.type,
                    status=c.status,
                    budget=float(c.budget or 0.0),
                    expectedRevenue=float(c.expected_revenue or 0.0),
                    startDate=c.start_date.isoformat() if c.start_date else None,
                    endDate=c.end_date.isoformat() if c.end_date else None,
                    description=c.description,
                    totalLeads=metrics["total_leads"],
                    totalDeals=metrics["total_deals"],
                    actualRevenue=metrics["actual_revenue"],
                    createdAt=c.created_at.isoformat() if c.created_at else None,
                )
            )
        return results

    @staticmethod
    def get_campaign_by_id(db: Session, campaign_id: str) -> CampaignDTO:
        c = CampaignRepository.get_by_id(db, campaign_id)
        if not c:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy chiến dịch với mã ID '{campaign_id}'.",
            )
        metrics = CampaignRepository.get_campaign_metrics(db, c.id)
        return CampaignDTO(
            id=c.id,
            name=c.name,
            code=c.code,
            type=c.type,
            status=c.status,
            budget=float(c.budget or 0.0),
            expectedRevenue=float(c.expected_revenue or 0.0),
            startDate=c.start_date.isoformat() if c.start_date else None,
            endDate=c.end_date.isoformat() if c.end_date else None,
            description=c.description,
            totalLeads=metrics["total_leads"],
            totalDeals=metrics["total_deals"],
            actualRevenue=metrics["actual_revenue"],
            createdAt=c.created_at.isoformat() if c.created_at else None,
        )

    @staticmethod
    def create_campaign(db: Session, dto: CreateCampaignDTO) -> CampaignDTO:
        existing = CampaignRepository.get_by_code(db, dto.code.strip())
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã chiến dịch '{dto.code}' đã tồn tại trên hệ thống. Vui lòng chọn mã khác.",
            )

        from datetime import date
        start_d = date.fromisoformat(dto.startDate) if dto.startDate else None
        end_d = date.fromisoformat(dto.endDate) if dto.endDate else None

        new_c = Campaign(
            id=str(uuid.uuid4()),
            name=dto.name.strip(),
            code=dto.code.strip().upper(),
            type=dto.type,
            status=dto.status,
            budget=dto.budget,
            expected_revenue=dto.expectedRevenue,
            start_date=start_d,
            end_date=end_d,
            description=dto.description,
        )
        saved = CampaignRepository.create(db, new_c)
        return CampaignDTO(
            id=saved.id,
            name=saved.name,
            code=saved.code,
            type=saved.type,
            status=saved.status,
            budget=float(saved.budget or 0.0),
            expectedRevenue=float(saved.expected_revenue or 0.0),
            startDate=saved.start_date.isoformat() if saved.start_date else None,
            endDate=saved.end_date.isoformat() if saved.end_date else None,
            description=saved.description,
            totalLeads=0,
            totalDeals=0,
            actualRevenue=0.0,
            createdAt=saved.created_at.isoformat() if saved.created_at else None,
        )

    @staticmethod
    def update_campaign(db: Session, campaign_id: str, dto: UpdateCampaignDTO) -> CampaignDTO:
        c = CampaignRepository.get_by_id(db, campaign_id)
        if not c:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy chiến dịch với mã ID '{campaign_id}'.",
            )
        from datetime import date
        if dto.name is not None:
            c.name = dto.name.strip()
        if dto.type is not None:
            c.type = dto.type
        if dto.status is not None:
            c.status = dto.status
        if dto.budget is not None:
            c.budget = dto.budget
        if dto.expectedRevenue is not None:
            c.expected_revenue = dto.expectedRevenue
        if dto.startDate is not None:
            c.start_date = date.fromisoformat(dto.startDate) if dto.startDate else None
        if dto.endDate is not None:
            c.end_date = date.fromisoformat(dto.endDate) if dto.endDate else None
        if dto.description is not None:
            c.description = dto.description

        saved = CampaignRepository.update(db, c)
        metrics = CampaignRepository.get_campaign_metrics(db, saved.id)
        return CampaignDTO(
            id=saved.id,
            name=saved.name,
            code=saved.code,
            type=saved.type,
            status=saved.status,
            budget=float(saved.budget or 0.0),
            expectedRevenue=float(saved.expected_revenue or 0.0),
            startDate=saved.start_date.isoformat() if saved.start_date else None,
            endDate=saved.end_date.isoformat() if saved.end_date else None,
            description=saved.description,
            totalLeads=metrics["total_leads"],
            totalDeals=metrics["total_deals"],
            actualRevenue=metrics["actual_revenue"],
            createdAt=saved.created_at.isoformat() if saved.created_at else None,
        )

    @staticmethod
    def delete_campaign(db: Session, campaign_id: str) -> dict:
        c = CampaignRepository.get_by_id(db, campaign_id)
        if not c:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy chiến dịch với mã ID '{campaign_id}'.",
            )
        CampaignRepository.delete(db, c)
        return {"success": True, "message": f"Đã xóa chiến dịch '{c.name}' thành công."}
