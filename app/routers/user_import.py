"""
Router API cho tính năng Nhập người dùng hàng loạt từ tệp Excel (SCRUM-79 / SCRUM-123 BE).
Bao gồm:
- GET  /api/v1/users/import/template : Tải tệp Excel mẫu chuẩn (.xlsx)
- POST /api/v1/users/import/preview  : Xem trước & kiểm tra tính hợp lệ của tệp Excel
- POST /api/v1/users/import/execute  : Thực thi nhập dữ liệu hàng loạt (bỏ qua dòng lỗi, nạp dòng hợp lệ)
Tất cả endpoints đều yêu cầu xác thực JWT Bearer và phân quyền Quản trị viên (Super Admin / Admin).
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.schemas.excel_import import (
    UserImportPreviewResponse,
    UserImportExecuteResponse,
)
from app.services.excel_import_service import ExcelImportService

router = APIRouter(prefix="/users/import", tags=["User Management - Import"])


@router.get(
    "/template",
    summary="Tải tệp Excel mẫu để nhập người dùng hàng loạt (SCRUM-79 / SCRUM-123 BE)",
    response_description="Tệp Excel mẫu (.xlsx)",
)
def download_user_import_template(
    current_user: User = Depends(require_admin),
):
    """
    Tải về tệp Excel mẫu (.xlsx) chuẩn gồm các cột:
    - full_name: Họ và tên
    - email: Địa chỉ email doanh nghiệp
    - phone: Số điện thoại liên hệ
    - role: Vai trò hệ thống
    - department: Phòng ban / Nhóm kinh doanh
    Chỉ tài khoản Quản trị hệ thống (Admin / Super Admin) mới có quyền truy cập.
    """
    return ExcelImportService.generate_template()


@router.post(
    "/preview",
    response_model=UserImportPreviewResponse,
    summary="Xem trước & kiểm tra tính hợp lệ của tệp Excel nhập người dùng (SCRUM-79 / SCRUM-123 BE)",
)
async def preview_user_import(
    file: UploadFile = File(..., description="Tệp Excel (.xlsx hoặc .xls)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserImportPreviewResponse:
    """
    Đọc và kiểm tra tính hợp lệ của tệp Excel tải lên mà KHÔNG ghi vào CSDL:
    - Kiểm tra trường bắt buộc (full_name, email, role).
    - Validate định dạng email, số điện thoại Việt Nam (10 chữ số).
    - Kiểm tra trùng lặp email (trong chính file và trong CSDL).
    - Kiểm tra vai trò hợp lệ trên hệ thống NexusCRM.
    """
    filename = (file.filename or "").lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ chấp nhận tệp định dạng Excel (.xlsx, .xls)",
        )

    file_bytes = await file.read()
    raw_rows = ExcelImportService.parse_excel_bytes(file_bytes)
    details, valid_count, error_count = ExcelImportService.validate_rows(raw_rows, db)

    return UserImportPreviewResponse(
        total_rows=len(raw_rows),
        valid_count=valid_count,
        error_count=error_count,
        details=details,
    )


@router.post(
    "/execute",
    response_model=UserImportExecuteResponse,
    summary="Thực thi nhập người dùng hàng loạt từ tệp Excel hoặc danh sách (SCRUM-79 / SCRUM-123 BE)",
)
async def execute_user_import(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserImportExecuteResponse:
    """
    Thực thi nhập dữ liệu hàng loạt:
    - Chấp nhận tệp Excel (multipart/form-data với trường 'file') hoặc danh sách JSON payload (application/json với trường 'rows').
    - Quy tắc nghiệp vụ bắt buộc: 'Dòng lỗi bị bỏ qua, dòng hợp lệ vẫn được nhập, có báo cáo tổng kết'.
    - Tạo tài khoản với mật khẩu mặc định (Password123!) được băm bảo mật Bcrypt.
    - Tự động gán Role, Team/Department và Data Scope tương ứng (OWN / TEAM / ALL).
    """
    content_type = request.headers.get("content-type", "").lower()
    raw_rows: List[Dict[str, Any]] = []

    if "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = form.get("file")
        if not file_obj or not hasattr(file_obj, "read"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng đính kèm tệp Excel (.xlsx) với trường 'file'.",
            )
        filename = (getattr(file_obj, "filename", "") or "").lower()
        if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chỉ chấp nhận tệp định dạng Excel (.xlsx, .xls)",
            )
        file_bytes = await file_obj.read()
        raw_rows = ExcelImportService.parse_excel_bytes(file_bytes)
    else:
        try:
            body_data = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dữ liệu yêu cầu không hợp lệ. Vui lòng gửi tệp Excel hoặc JSON payload.",
            )
        if isinstance(body_data, dict):
            rows_list = body_data.get("rows") or body_data.get("users") or []
        elif isinstance(body_data, list):
            rows_list = body_data
        else:
            rows_list = []
        raw_rows = ExcelImportService.normalize_json_rows(rows_list)

    return ExcelImportService.execute_import(raw_rows, db)
