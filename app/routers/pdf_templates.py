from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.pdf_template import PdfTemplateDTO, CreatePdfTemplateDTO, UpdatePdfTemplateDTO
from app.services.pdf_template_service import PdfTemplateService

router = APIRouter(prefix="/pdf-templates", tags=["PDF Templates Configuration (S7-05)"])


@router.get("", response_model=List[PdfTemplateDTO], summary="Lấy danh sách các mẫu PDF có thể cấu hình (S7-05)")
def get_templates(
    templateType: Optional[str] = Query(None, description="Lọc theo quotation hoặc contract"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PdfTemplateDTO]:
    return PdfTemplateService.get_templates(db=db, template_type=templateType)


@router.post("", response_model=PdfTemplateDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mẫu PDF mới (S7-05)")
def create_template(
    dto: CreatePdfTemplateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PdfTemplateDTO:
    return PdfTemplateService.create_template(db=db, dto=dto)


@router.put("/{template_id}", response_model=PdfTemplateDTO, summary="Cập nhật mẫu PDF (S7-05)")
def update_template(
    template_id: str,
    dto: UpdatePdfTemplateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PdfTemplateDTO:
    return PdfTemplateService.update_template(db=db, template_id=template_id, dto=dto)
