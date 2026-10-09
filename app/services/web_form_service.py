import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models.web_form import WebForm
from app.models.lead import Lead
from app.schemas.web_form import (
    WebFormCreate,
    WebFormUpdate,
    PublicLeadSubmitRequest,
    PublicLeadSubmitResponse,
)


class InMemoryIPRateLimiter:
    """
    Bộ đếm giới hạn tần suất theo địa chỉ IP Client (SCRUM-24 / S4-01).
    Thuật toán Sliding Window: Tối đa 5 lượt submit / phút / IP.
    """
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._records: Dict[str, List[float]] = {}

    def check_and_record(self, ip: str) -> None:
        """
        Kiểm tra và ghi nhận lượt request. Nếu vượt quá max_requests trong window_seconds -> raise 429.
        """
        now = time.time()
        client_history = self._records.get(ip, [])

        # Lọc bỏ các timestamp cũ ngoài khung thời gian window_seconds
        valid_history = [t for t in client_history if now - t < self.window_seconds]

        if len(valid_history) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - valid_history[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quá nhiều yêu cầu gửi biểu mẫu từ địa chỉ IP của bạn ({ip}). Giới hạn tối đa {self.max_requests} lượt/phút. Vui lòng thử lại sau.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        valid_history.append(now)
        self._records[ip] = valid_history

    def reset(self) -> None:
        """Reset bộ nhớ rate limit (dùng cho tests)."""
        self._records.clear()


# Singleton rate limiter
ip_rate_limiter = InMemoryIPRateLimiter(max_requests=5, window_seconds=60)


class WebFormService:
    """Service xử lý nghiệp vụ Quản lý Biểu mẫu nhúng và Thu thập Lead (SCRUM-24)."""

    @staticmethod
    def generate_form_key() -> str:
        """Sinh chuỗi form_key định danh duy nhất bảo mật."""
        return f"wf_{uuid.uuid4().hex}"

    @staticmethod
    def build_embed_code(form_key: str, base_url: str = "http://localhost:8000") -> str:
        """Sinh đoạn mã HTML / Script dán vào website bất kỳ."""
        return (
            f'<!-- NexusCRM Lead Capture Form Embed (SCRUM-24) -->\n'
            f'<div id="crm-lead-form" data-form-key="{form_key}"></div>\n'
            f'<script src="{base_url}/static/form-loader.js" data-form-key="{form_key}" async></script>'
        )

    @staticmethod
    def build_iframe_code(form_key: str, base_url: str = "http://localhost:8000") -> str:
        """Sinh đoạn mã nhúng dạng Iframe độc lập."""
        return (
            f'<iframe src="{base_url}/api/v1/public/forms/{form_key}/render" '
            f'width="100%" height="560" frameborder="0" '
            f'style="border:none; max-width:640px; width:100%; border-radius:12px; box-shadow:0 8px 24px rgba(0,0,0,0.06);">'
            f'</iframe>'
        )

    # ---------------------------------------------------------
    # Quản trị Biểu mẫu (Marketing / Admin)
    # ---------------------------------------------------------

    def create_form(self, db: Session, dto: WebFormCreate, user_id: Optional[str] = None) -> WebForm:
        """Tạo cấu hình biểu mẫu nhúng mới."""
        form_key = self.generate_form_key()
        form = WebForm(
            id=str(uuid.uuid4()),
            name=dto.name.strip(),
            form_key=form_key,
            lead_source=dto.lead_source.strip() or "Website Form",
            is_active=dto.is_active,
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(form)
        db.commit()
        db.refresh(form)
        return form

    def get_forms(self, db: Session, page: int = 1, limit: int = 50) -> Tuple[List[WebForm], int, Dict[str, int]]:
        """Lấy danh sách các biểu mẫu kèm tổng số lead đã thu thập."""
        query = db.query(WebForm)
        total = query.count()
        forms = query.order_by(WebForm.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

        # Đếm số lượng lead theo từng form
        lead_counts = {}
        if forms:
            form_ids = [f.id for f in forms]
            count_rows = (
                db.query(Lead.form_id, func.count(Lead.id))
                .filter(Lead.form_id.in_(form_ids))
                .group_by(Lead.form_id)
                .all()
            )
            lead_counts = {row[0]: row[1] for row in count_rows if row[0]}

        return forms, total, lead_counts

    def get_form_by_id(self, db: Session, form_id: str) -> WebForm:
        """Lấy chi tiết biểu mẫu theo ID."""
        form = db.query(WebForm).filter(WebForm.id == form_id).first()
        if not form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy biểu mẫu với ID '{form_id}'.",
            )
        return form

    def get_form_by_key(self, db: Session, form_key: str) -> WebForm:
        """Lấy biểu mẫu theo form_key công khai."""
        form = db.query(WebForm).filter(WebForm.form_key == form_key).first()
        if not form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Biểu mẫu không tồn tại hoặc khóa biểu mẫu không hợp lệ.",
            )
        return form

    def update_form(self, db: Session, form_id: str, dto: WebFormUpdate) -> WebForm:
        """Cập nhật biểu mẫu."""
        form = self.get_form_by_id(db, form_id)
        if dto.name is not None:
            form.name = dto.name.strip()
        if dto.lead_source is not None:
            form.lead_source = dto.lead_source.strip()
        if dto.is_active is not None:
            form.is_active = dto.is_active
        form.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(form)
        return form

    def delete_form(self, db: Session, form_id: str) -> None:
        """Xóa biểu mẫu."""
        form = self.get_form_by_id(db, form_id)
        db.delete(form)
        db.commit()

    # ---------------------------------------------------------
    # Public Endpoint: Tiếp nhận Submit Lead từ Website
    # ---------------------------------------------------------

    def submit_lead_from_public_form(
        self,
        db: Session,
        form_key: str,
        payload: PublicLeadSubmitRequest,
        client_ip: Optional[str] = None,
    ) -> PublicLeadSubmitResponse:
        """
        Xử lý submit thông tin lead từ biểu mẫu web công khai:
        1. Kiểm tra giới hạn tần suất IP (Rate limiting 5 req/min) -> 429
        2. Kiểm tra Honeypot (_hp / website_hp) -> Bot spam -> Silent success
        3. Kiểm tra tính hợp lệ & trạng thái hoạt động của form_key -> 400
        4. Tạo bản ghi Lead mới (status='NEW', source=form.lead_source)
        """
        # 1. IP Rate Limiting
        ip = client_ip or "127.0.0.1"
        ip_rate_limiter.check_and_record(ip)

        # 2. Honeypot check (Chống spam tự động)
        # Nếu bot điền bất kỳ giá trị nào vào trường honeypot ẩn -> âm thầm bỏ qua
        if payload.is_bot_spam:
            return PublicLeadSubmitResponse(
                success=True,
                message="Gửi thông tin tư vấn thành công! Bộ phận kinh doanh sẽ sớm liên hệ với bạn.",
                lead_id=None,
            )

        # 3. Lấy thông tin form
        form = db.query(WebForm).filter(WebForm.form_key == form_key).first()
        if not form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Biểu mẫu không tồn tại trên hệ thống.",
            )

        if not form.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Biểu mẫu hiện đã ngừng tiếp nhận thông tin đăng ký.",
            )

        # 4. Tạo Lead mới
        new_lead = Lead(
            id=str(uuid.uuid4()),
            full_name=payload.full_name.strip(),
            email=payload.email.strip().lower(),
            phone=payload.phone.strip(),
            company=payload.company.strip() if payload.company else None,
            interest_need=payload.interest_need.strip() if payload.interest_need else None,
            source=form.lead_source or form.name,
            status="NEW",
            form_id=form.id,
            client_ip=ip,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_lead)
        db.commit()
        db.refresh(new_lead)

        return PublicLeadSubmitResponse(
            success=True,
            message="Gửi thông tin tư vấn thành công! Bộ phận kinh doanh sẽ sớm liên hệ với bạn.",
            lead_id=new_lead.id,
        )

    # ---------------------------------------------------------
    # Quản lý Danh sách Leads (Marketing / Sales)
    # ---------------------------------------------------------

    def get_leads(
        self,
        db: Session,
        status_filter: Optional[str] = None,
        form_id: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Lead], int]:
        """Truy vấn danh sách Leads với bộ lọc linh hoạt."""
        query = db.query(Lead)

        if status_filter and status_filter.upper() != "ALL":
            query = query.filter(Lead.status == status_filter.upper())

        if form_id:
            query = query.filter(Lead.form_id == form_id)

        if source:
            query = query.filter(Lead.source.ilike(f"%{source}%"))

        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Lead.full_name.ilike(s),
                    Lead.email.ilike(s),
                    Lead.phone.ilike(s),
                    Lead.company.ilike(s),
                )
            )

        total = query.count()
        leads = (
            query.order_by(Lead.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return leads, total

    def update_lead_status(self, db: Session, lead_id: str, new_status: str) -> Lead:
        """Cập nhật trạng thái xử lý của Lead."""
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy Lead với ID '{lead_id}'.",
            )
        valid_statuses = {"NEW", "CONTACTED", "QUALIFIED", "CONVERTED", "REJECTED"}
        normalized_status = new_status.strip().upper()
        if normalized_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trạng thái '{new_status}' không hợp lệ. Cho phép: {', '.join(valid_statuses)}.",
            )
        lead.status = normalized_status
        lead.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(lead)
        return lead


web_form_service = WebFormService()
