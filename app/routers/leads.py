"""
Router API cho phân hệ Quản lý Lead (SCRUM-40 / Sprint 4).
Hỗ trợ:
- POST /api/v1/leads/manual: Tạo lead thủ công (bắt buộc có nguồn - Lead Source Requirement).
- GET  /api/v1/leads/import/template: Tải tệp Excel mẫu chuẩn (.xlsx).
- POST /api/v1/leads/import/preview: Xem trước và kiểm tra lỗi chi tiết từng dòng.
- POST /api/v1/leads/import/execute: Thực thi lưu các bản ghi hợp lệ vào CSDL theo Transaction.
- GET  /api/v1/leads: Lấy danh sách Leads (tìm kiếm & phân trang).
- GET  /api/v1/leads/{lead_id}: Xem chi tiết một Lead.
Roles hỗ trợ: MARKETING, SALES_REP, ADMIN.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, UploadFile, File, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.lead import Lead
from app.schemas.lead_import import (
    LeadCreateManualRequest,
    LeadResponse,
    LeadImportPreviewResponse,
    LeadImportExecuteRequest,
    LeadImportExecuteResponse,
)
from app.services.lead_service import LeadService

router = APIRouter(prefix="/leads", tags=["Lead Management (SCRUM-40 / Sprint 4)"])

LEAD_ALLOWED_ROLES = {
    "marketing",
    "marketing staff",
    "nhân viên marketing",
    "sales",
    "sales_rep",
    "sales rep",
    "account executive",
    "nhân viên kinh doanh",
    "employee",
    "sales manager",
    "team leader",
    "trưởng nhóm kinh doanh",
    "sales director",
    "vp of sales",
    "giám đốc kinh doanh",
    "admin",
    "super admin",
    "quản trị viên",
    "revops",
    "revops lead",
}


def require_lead_role(current_user: User = Depends(get_current_user)) -> User:
    """Xác thực người dùng có vai trò Marketing, Sales hoặc Admin."""
    role = (current_user.role or "").strip().lower()
    if role and role not in LEAD_ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thao tác quản lý Lead (Yêu cầu quyền Marketing, Sales hoặc Quản trị viên).",
        )
    return current_user


@router.post(
    "/manual",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo một Lead thủ công từ sự kiện hoặc danh thiếp (SCRUM-40 AC1 & AC2)",
)
def create_manual_lead(
    request: LeadCreateManualRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_role),
) -> LeadResponse:
    """
    Tạo thủ công 1 lead:
    - Bắt buộc có: `full_name`, `phone`, và `source` (Nguồn lead).
    - Tùy chọn: `email`, `company`, `interest_need`, `notes`.
    - Trạng thái mặc định: `status = 'NEW'`.
    - Gắn `created_by = current_user.id`.
    """
    lead = LeadService.create_manual_lead(db=db, request=request, current_user=current_user)
    return LeadResponse.model_validate(lead)


@router.get(
    "/import/template",
    summary="Tải tệp Excel mẫu để nhập Lead hàng loạt (SCRUM-40 AC3)",
    response_description="Tệp Excel mẫu chuẩn (.xlsx)",
)
def download_lead_import_template(
    current_user: User = Depends(require_lead_role),
):
    """
    Tải về tệp Excel mẫu (.xlsx) chuẩn gồm các cột:
    - `full_name`: Họ và tên (bắt buộc)
    - `phone`: Số điện thoại (bắt buộc, 10 số VN)
    - `email`: Địa chỉ email
    - `company`: Công ty / Doanh nghiệp
    - `interest_need`: Nhu cầu quan tâm
    - `source`: Nguồn lead (bắt buộc)
    - `notes`: Ghi chú
    kèm dữ liệu mẫu minh họa.
    """
    return LeadService.generate_template()


@router.post(
    "/import/preview",
    response_model=LeadImportPreviewResponse,
    summary="Xem trước & kiểm tra lỗi chi tiết từng dòng tệp Excel/CSV (SCRUM-40 AC3)",
)
async def preview_lead_import(
    file: UploadFile = File(..., description="Tệp Excel (.xlsx, .xls) hoặc CSV (.csv), tối đa 10MB"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_role),
) -> LeadImportPreviewResponse:
    """
    Đọc tệp tải lên mà không lưu vào DB (Dry-run preview):
    - Validate từng dòng: thiếu `full_name`, `phone`, `source`; sai định dạng email; sai số ĐT VN.
    - Quét phát hiện trùng lặp trong tệp và trong CSDL.
    - Trả về số dòng hợp lệ, số dòng lỗi và danh sách lỗi chi tiết theo từng dòng (`errors: list[str]`).
    """
    return await LeadService.preview_import(file=file, db=db, current_user=current_user)


@router.post(
    "/import/execute",
    response_model=LeadImportExecuteResponse,
    status_code=status.HTTP_200_OK,
    summary="Thực thi nhập dữ liệu Lead hàng loạt vào CSDL theo Transaction (SCRUM-40 AC3)",
)
def execute_lead_import(
    request: LeadImportExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_role),
) -> LeadImportExecuteResponse:
    """
    Thực thi lưu các dòng hợp lệ vào CSDL:
    - Bỏ qua các dòng lỗi validation.
    - Gắn `created_by = current_user.id`, `status = 'NEW'`.
    - Thực hiện an toàn trong một Database Transaction (rollback khi có sự cố).
    - Trả về báo cáo tổng kết kết quả.
    """
    return LeadService.execute_import(db=db, request=request, current_user=current_user)


@router.get(
    "",
    response_model=List[LeadResponse],
    summary="Lấy danh sách Lead có tìm kiếm và phân trang",
)
def get_leads(
    search: Optional[str] = Query(None, description="Tìm theo tên, điện thoại, email, công ty"),
    source: Optional[str] = Query(None, description="Lọc theo nguồn lead"),
    campaign_id: Optional[str] = Query(None, description="Lọc theo chiến dịch tiếp thị"),
    status_filter: Optional[str] = Query(None, alias="status", description="Lọc theo trạng thái"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_role),
) -> List[LeadResponse]:
    query = db.query(Lead)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Lead.full_name.ilike(s)) |
            (Lead.phone.ilike(s)) |
            (Lead.email.ilike(s)) |
            (Lead.company.ilike(s))
        )
    if source:
        query = query.filter(Lead.source == source)
    if campaign_id:
        query = query.filter(Lead.campaign_id == campaign_id)
    if status_filter:
        query = query.filter(Lead.status == status_filter)

    leads = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
    return [LeadResponse.model_validate(l) for l in leads]


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Xem chi tiết một Lead theo ID",
)
def get_lead_by_id(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_role),
) -> LeadResponse:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy Lead trong hệ thống.",
        )
    return LeadResponse.model_validate(lead)
