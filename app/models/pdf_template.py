import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from app.database import Base


class PdfTemplate(Base):
    """
    S7-05: Mẫu Báo giá & Hợp đồng PDF có thể cấu hình linh hoạt (không hardcode).
    Lưu trữ logo, thông tin doanh nghiệp, điều khoản, mẫu định dạng.
    """
    __tablename__ = "pdf_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    template_type = Column(String(50), default="quotation", nullable=False, index=True)  # quotation | contract
    logo_url = Column(String(500), nullable=True)
    company_name = Column(String(255), nullable=False, default="CÔNG TY CỔ PHẦN CÔNG NGHỆ NEXUS VIỆT NAM")
    company_tax_code = Column(String(50), nullable=True, default="0108889999")
    company_address = Column(String(255), nullable=True, default="Tòa nhà Nexus Tower, 180 Cầu Giấy, Hà Nội")
    company_phone = Column(String(50), nullable=True, default="1900 6868 - 024 3799 8888")
    company_email = Column(String(100), nullable=True, default="contact@nexuscrm.vn")
    company_bank_account = Column(String(100), nullable=True, default="19036888899999 - Ngân hàng Techcombank")
    header_text = Column(Text, nullable=True)
    footer_text = Column(Text, nullable=True, default="NexusCRM — Nền tảng Quản trị Quan hệ Khách hàng Doanh nghiệp.")
    terms_and_conditions = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
