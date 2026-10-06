"""
Router API cho tính năng Nhập danh sách khách hàng hàng loạt từ Excel (SCRUM-64 / S3-06).
Bao gồm:
- GET  /api/v1/customers/import/template : Tải tệp Excel mẫu chuẩn (.xlsx)
- POST /api/v1/customers/import/preview  : Xem trước & kiểm tra tính hợp lệ của tệp tải lên (dry-run preview)
- POST /api/v1/customers/import/execute  : Thực thi nhập dữ liệu vào CSDL kèm xử lý trùng lặp (SKIP/UPDATE)
Role hỗ trợ: SALES_REP, TEAM_LEAD, DIRECTOR, ADMIN.
"""
from fastapi import APIRouter, Depends, status, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.customer_import import (
    CustomerImportPreviewResponse,
    CustomerImportExecuteRequest,
    CustomerImportSummaryResponse,
)
from app.services.customer_import_service import CustomerImportService

router = APIRouter(prefix="/customers/import", tags=["Customer Management - Bulk Import"])


@router.get(
    "/template",
    summary="Tải tệp Excel mẫu để nhập khách hàng hàng loạt (SCRUM-64)",
    response_description="Tệp Excel mẫu (.xlsx)",
)
def download_customer_import_template(
    current_user: User = Depends(get_current_user),
):
    """
    Tải về tệp Excel mẫu (.xlsx) chuẩn gồm các cột:
    - name: Tên khách hàng / doanh nghiệp (bắt buộc)
    - tax_code: Mã số thuế (10 hoặc 13 chữ số)
    - email: Địa chỉ email liên hệ
    - phone: Số điện thoại liên hệ
    - website: Website / tên miền công ty
    - address: Địa chỉ văn phòng / trụ sở
    - status: Trạng thái (LEAD, CONTACTED, CUSTOMER)
    """
    return CustomerImportService.generate_template()


@router.post(
    "/preview",
    response_model=CustomerImportPreviewResponse,
    summary="Xem trước & kiểm tra tính hợp lệ của tệp Excel/CSV nhập khách hàng (SCRUM-64)",
)
async def preview_customer_import(
    file: UploadFile = File(..., description="Tệp Excel (.xlsx) hoặc CSV (.csv), tối đa 5MB"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerImportPreviewResponse:
    """
    Đọc và kiểm tra tính hợp lệ của tệp Excel/CSV tải lên mà KHÔNG ghi vào CSDL:
    - Kiểm tra trường bắt buộc (name: từ 2 đến 150 ký tự).
    - Validate định dạng tax_code (10 hoặc 13 chữ số), email, số điện thoại Việt Nam (10 chữ số).
    - Quét phát hiện trùng lặp CSDL theo tax_code và website (loại trừ bản ghi đã xóa mềm).
    - Phát hiện trùng lặp nội bộ trong cùng tệp tải lên.
    - Trả về danh sách chi tiết từng dòng kèm cờ is_valid, danh sách errors và cờ is_duplicate.
    """
    return await CustomerImportService.preview_import(file=file, db=db, current_user=current_user)


@router.post(
    "/execute",
    response_model=CustomerImportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Thực thi nhập dữ liệu khách hàng vào hệ thống (SCRUM-64)",
)
def execute_customer_import(
    request: CustomerImportExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerImportSummaryResponse:
    """
    Thực thi lưu danh sách khách hàng vào CSDL:
    - Bỏ qua các dòng lỗi validation (is_valid == False).
    - Xử lý bản ghi trùng lặp theo tùy chọn:
      + 'SKIP': Bỏ qua, không ghi đè.
      + 'UPDATE': Cập nhật thông tin mới vào khách hàng đã có.
    - Tạo mới các bản ghi hợp lệ và gán quyền sở hữu cho người dùng thực hiện.
    - Toàn bộ thao tác thực hiện trong một Transaction an toàn.
    """
    return CustomerImportService.execute_import(request=request, db=db, current_user=current_user)
