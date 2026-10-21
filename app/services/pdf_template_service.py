import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.pdf_template import PdfTemplate
from app.schemas.pdf_template import CreatePdfTemplateDTO, UpdatePdfTemplateDTO, PdfTemplateDTO


class PdfTemplateService:
    """
    S7-05: Quản lý Mẫu Báo giá & Hợp đồng PDF có thể cấu hình linh hoạt.
    """

    @staticmethod
    def get_templates(db: Session, template_type: Optional[str] = None) -> List[PdfTemplateDTO]:
        query = db.query(PdfTemplate)
        if template_type:
            query = query.filter(PdfTemplate.template_type == template_type)
        templates = query.order_by(PdfTemplate.is_default.desc(), PdfTemplate.created_at.desc()).all()
        return [
            PdfTemplateDTO(
                id=t.id,
                name=t.name,
                templateType=t.template_type,
                logoUrl=t.logo_url,
                companyName=t.company_name,
                companyTaxCode=t.company_tax_code,
                companyAddress=t.company_address,
                companyPhone=t.company_phone,
                companyEmail=t.company_email,
                companyBankAccount=t.company_bank_account,
                headerText=t.header_text,
                footerText=t.footer_text,
                termsAndConditions=t.terms_and_conditions,
                isDefault=t.is_default,
                createdAt=t.created_at.isoformat() if t.created_at else None,
                updatedAt=t.updated_at.isoformat() if t.updated_at else None,
            )
            for t in templates
        ]

    @staticmethod
    def get_template_by_id(db: Session, template_id: str) -> Optional[PdfTemplate]:
        return db.query(PdfTemplate).filter(PdfTemplate.id == template_id).first()

    @staticmethod
    def get_default_template(db: Session, template_type: str = "quotation") -> Optional[PdfTemplate]:
        tpl = db.query(PdfTemplate).filter(
            PdfTemplate.template_type == template_type,
            PdfTemplate.is_default == True,
        ).first()
        if not tpl:
            tpl = db.query(PdfTemplate).filter(PdfTemplate.template_type == template_type).first()
        return tpl

    @staticmethod
    def create_template(db: Session, dto: CreatePdfTemplateDTO) -> PdfTemplateDTO:
        if dto.isDefault:
            # Bỏ cờ default của các mẫu cùng loại khác
            db.query(PdfTemplate).filter(PdfTemplate.template_type == dto.templateType).update({"is_default": False})

        new_t = PdfTemplate(
            id=str(uuid.uuid4()),
            name=dto.name,
            template_type=dto.templateType,
            logo_url=dto.logoUrl,
            company_name=dto.companyName,
            company_tax_code=dto.companyTaxCode,
            company_address=dto.companyAddress,
            company_phone=dto.companyPhone,
            company_email=dto.companyEmail,
            company_bank_account=dto.companyBankAccount,
            header_text=dto.headerText,
            footer_text=dto.footerText,
            terms_and_conditions=dto.termsAndConditions,
            is_default=dto.isDefault,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_t)
        db.commit()
        db.refresh(new_t)

        return PdfTemplateDTO(
            id=new_t.id,
            name=new_t.name,
            templateType=new_t.template_type,
            logoUrl=new_t.logo_url,
            companyName=new_t.company_name,
            companyTaxCode=new_t.company_tax_code,
            companyAddress=new_t.company_address,
            companyPhone=new_t.company_phone,
            companyEmail=new_t.company_email,
            companyBankAccount=new_t.company_bank_account,
            headerText=new_t.header_text,
            footerText=new_t.footer_text,
            termsAndConditions=new_t.terms_and_conditions,
            isDefault=new_t.is_default,
            createdAt=new_t.created_at.isoformat(),
            updatedAt=new_t.updated_at.isoformat(),
        )

    @staticmethod
    def update_template(db: Session, template_id: str, dto: UpdatePdfTemplateDTO) -> PdfTemplateDTO:
        t = db.query(PdfTemplate).filter(PdfTemplate.id == template_id).first()
        if not t:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mẫu PDF.")

        if dto.isDefault:
            db.query(PdfTemplate).filter(
                PdfTemplate.template_type == (dto.templateType or t.template_type),
                PdfTemplate.id != template_id,
            ).update({"is_default": False})

        for k, v in dto.model_dump(exclude_unset=True).items():
            db_k = "template_type" if k == "templateType" else \
                   "logo_url" if k == "logoUrl" else \
                   "company_name" if k == "companyName" else \
                   "company_tax_code" if k == "companyTaxCode" else \
                   "company_address" if k == "companyAddress" else \
                   "company_phone" if k == "companyPhone" else \
                   "company_email" if k == "companyEmail" else \
                   "company_bank_account" if k == "companyBankAccount" else \
                   "header_text" if k == "headerText" else \
                   "footer_text" if k == "footerText" else \
                   "terms_and_conditions" if k == "termsAndConditions" else \
                   "is_default" if k == "isDefault" else k
            setattr(t, db_k, v)

        t.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(t)

        return PdfTemplateDTO(
            id=t.id,
            name=t.name,
            templateType=t.template_type,
            logoUrl=t.logo_url,
            companyName=t.company_name,
            companyTaxCode=t.company_tax_code,
            companyAddress=t.company_address,
            companyPhone=t.company_phone,
            companyEmail=t.company_email,
            companyBankAccount=t.company_bank_account,
            headerText=t.header_text,
            footerText=t.footer_text,
            termsAndConditions=t.terms_and_conditions,
            isDefault=t.is_default,
            createdAt=t.created_at.isoformat(),
            updatedAt=t.updated_at.isoformat(),
        )
