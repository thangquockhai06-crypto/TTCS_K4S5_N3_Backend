from math import ceil
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.web_form import (
    WebFormCreate,
    WebFormUpdate,
    WebFormResponse,
    WebFormEmbedCodeResponse,
    LeadResponse,
    LeadListResponse,
    LeadStatusUpdate,
)
from app.services.web_form_service import web_form_service

router = APIRouter(tags=["Web Forms & Lead Capture (SCRUM-24 / EP-04)"])


def _get_base_url(request: Request) -> str:
    """Xác định Base URL từ request hiện tại."""
    base_url = str(request.base_url).rstrip("/")
    # Nếu client gọi qua proxy hoặc localhost chuẩn
    return base_url or "http://localhost:8000"


# ==============================================================================
# 1. Quản trị Biểu mẫu nhúng (Marketing / Admin) - Yêu cầu JWT
# ==============================================================================

@router.post(
    "/forms",
    response_model=WebFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo biểu mẫu nhúng website mới (SCRUM-24)",
)
def create_web_form(
    dto: WebFormCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Tạo biểu mẫu thu thập lead nhúng trên website.
    Tự động sinh `form_key` định danh duy nhất và gắn người tạo.
    """
    form = web_form_service.create_form(db=db, dto=dto, user_id=current_user.id)
    base_url = _get_base_url(request)
    embed_code = web_form_service.build_embed_code(form.form_key, base_url)
    iframe_code = web_form_service.build_iframe_code(form.form_key, base_url)

    res = WebFormResponse.model_validate(form)
    res.embed_code = embed_code
    res.iframe_code = iframe_code
    res.total_leads = 0
    return res


@router.get(
    "/forms",
    response_model=List[WebFormResponse],
    summary="Lấy danh sách các biểu mẫu nhúng website (SCRUM-24)",
)
def list_web_forms(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách tất cả biểu mẫu nhúng kèm tổng số lead đã thu thập và đoạn mã nhúng.
    """
    forms, total, lead_counts = web_form_service.get_forms(db=db, page=page, limit=limit)
    base_url = _get_base_url(request)

    result = []
    for f in forms:
        item = WebFormResponse.model_validate(f)
        item.embed_code = web_form_service.build_embed_code(f.form_key, base_url)
        item.iframe_code = web_form_service.build_iframe_code(f.form_key, base_url)
        item.total_leads = lead_counts.get(f.id, 0)
        result.append(item)
    return result


@router.get(
    "/forms/{id}",
    response_model=WebFormResponse,
    summary="Xem chi tiết một biểu mẫu nhúng (SCRUM-24)",
)
def get_web_form(
    id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy thông tin chi tiết của biểu mẫu theo ID."""
    form = web_form_service.get_form_by_id(db=db, form_id=id)
    base_url = _get_base_url(request)

    leads, count = web_form_service.get_leads(db=db, form_id=id, limit=1)
    res = WebFormResponse.model_validate(form)
    res.embed_code = web_form_service.build_embed_code(form.form_key, base_url)
    res.iframe_code = web_form_service.build_iframe_code(form.form_key, base_url)
    res.total_leads = count
    return res


@router.get(
    "/forms/{id}/embed-code",
    response_model=WebFormEmbedCodeResponse,
    summary="Sinh mã nhúng HTML/Script cho biểu mẫu (SCRUM-24)",
)
def get_embed_code(
    id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sinh mã HTML nhúng script và mã Iframe chuẩn để nhân viên Marketing dán vào website.
    """
    form = web_form_service.get_form_by_id(db=db, form_id=id)
    base_url = _get_base_url(request)
    embed_code = web_form_service.build_embed_code(form.form_key, base_url)
    iframe_code = web_form_service.build_iframe_code(form.form_key, base_url)
    direct_submit_url = f"{base_url}/api/v1/public/forms/{form.form_key}/submit"

    return WebFormEmbedCodeResponse(
        form_id=form.id,
        form_name=form.name,
        form_key=form.form_key,
        lead_source=form.lead_source,
        is_active=form.is_active,
        embed_code=embed_code,
        iframe_code=iframe_code,
        direct_submit_url=direct_submit_url,
    )


@router.put(
    "/forms/{id}",
    response_model=WebFormResponse,
    summary="Cập nhật cấu hình biểu mẫu nhúng (SCRUM-24)",
)
def update_web_form(
    id: str,
    dto: WebFormUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chỉnh sửa tên form, nguồn khách hàng tiềm năng hoặc kích hoạt/vô hiệu hóa."""
    form = web_form_service.update_form(db=db, form_id=id, dto=dto)
    base_url = _get_base_url(request)
    res = WebFormResponse.model_validate(form)
    res.embed_code = web_form_service.build_embed_code(form.form_key, base_url)
    res.iframe_code = web_form_service.build_iframe_code(form.form_key, base_url)
    return res


@router.delete(
    "/forms/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa biểu mẫu nhúng (SCRUM-24)",
)
def delete_web_form(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa cấu hình biểu mẫu."""
    web_form_service.delete_form(db=db, form_id=id)
    return None


@router.get(
    "/forms/{id}/leads",
    response_model=List[LeadResponse],
    summary="Lấy danh sách các lead thu thập từ biểu mẫu cụ thể (SCRUM-24)",
)
def get_leads_for_form(
    id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xem danh sách các khách hàng tiềm năng thu thập từ một form nhất định."""
    leads, _ = web_form_service.get_leads(db=db, form_id=id, page=page, limit=limit)
    return [LeadResponse.model_validate(l) for l in leads]


# ==============================================================================
# 2. Quản lý Danh sách Lead tổng thể (EP-04)
# ==============================================================================

@router.get(
    "/leads",
    response_model=LeadListResponse,
    summary="Lấy danh sách toàn bộ Leads trong hệ thống (EP-04)",
)
def list_leads(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (NEW, CONTACTED, QUALIFIED...)"),
    form_id: Optional[str] = Query(None, description="Lọc theo Form ID"),
    source: Optional[str] = Query(None, description="Lọc theo nguồn (Website Form, Facebook...)"),
    q: Optional[str] = Query(None, description="Tìm kiếm theo tên, email, sđt, công ty"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách khách hàng tiềm năng (Leads) đã thu thập được từ web form và các kênh khác,
    kèm phân trang và bộ lọc trạng thái.
    """
    leads, total = web_form_service.get_leads(
        db=db,
        status_filter=status,
        form_id=form_id,
        source=source,
        search=q,
        page=page,
        limit=limit,
    )
    total_pages = ceil(total / limit) if total > 0 else 1

    return LeadListResponse(
        items=[LeadResponse.model_validate(l) for l in leads],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.put(
    "/leads/{id}/status",
    response_model=LeadResponse,
    summary="Cập nhật trạng thái xử lý của Lead (EP-04)",
)
def update_lead_status(
    id: str,
    dto: LeadStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cập nhật trạng thái của Lead (ví dụ: NEW -> CONTACTED -> QUALIFIED)."""
    lead = web_form_service.update_lead_status(db=db, lead_id=id, new_status=dto.status)
    return LeadResponse.model_validate(lead)
