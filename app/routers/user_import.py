"""
Router API cho tính năng Nhập người dùng hàng loạt từ tệp Excel / CSV (SCRUM-79 / SCRUM-123 BE & Bulk Import Upgrade).
Bao gồm:
- GET  /api/v1/users/import/template : Tải tệp Excel mẫu chuẩn (.xlsx) hoặc CSV mẫu (.csv)
- POST /api/v1/users/import/preview  : Xem trước & kiểm tra tính hợp lệ của tệp Excel / CSV
- POST /api/v1/users/import/execute  : Thực thi nhập dữ liệu hàng loạt đồng bộ
- POST /api/v1/users/import/jobs     : Khởi tạo tiến trình nhập hàng loạt chạy nền (Background Job)
- GET  /api/v1/users/import/jobs     : Danh sách các công việc nhập gần đây
- GET  /api/v1/users/import/jobs/{id}: Xem trạng thái và tiến độ xử lý của công việc nhập
- GET  /api/v1/users/import/jobs/{id}/errors.csv: Tải về báo cáo tệp lỗi dạng CSV
Tất cả endpoints đều yêu cầu xác thực JWT Bearer và phân quyền Quản trị viên (Super Admin / Admin).
"""
import io
import json
from typing import List, Dict, Any, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Request,
    Query,
    BackgroundTasks,
)
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.models.user_import_job import UserImportJob
from app.schemas.excel_import import (
    UserImportPreviewResponse,
    UserImportExecuteResponse,
    UserImportJobResponse,
)
from app.services.excel_import_service import ExcelImportService

router = APIRouter(prefix="/users/import", tags=["User Management - Import"])


@router.get(
    "/template",
    summary="Tải tệp mẫu Excel hoặc CSV để nhập người dùng hàng loạt",
    response_description="Tệp mẫu (.xlsx hoặc .csv)",
)
def download_user_import_template(
    format: str = Query("xlsx", description="Định dạng tệp: xlsx hoặc csv"),
    current_user: User = Depends(require_admin),
):
    """
    Tải về tệp mẫu chuẩn gồm các cột:
    - full_name: Họ và tên
    - email: Địa chỉ email doanh nghiệp
    - phone: Số điện thoại liên hệ
    - role: Vai trò hệ thống
    - department: Phòng ban / Nhóm kinh doanh
    """
    fmt = format.lower().strip()
    if fmt == "csv":
        return ExcelImportService.generate_template(format_type="csv")
    return ExcelImportService.generate_template(format_type="xlsx")


@router.post(
    "/preview",
    response_model=UserImportPreviewResponse,
    summary="Xem trước & kiểm tra tính hợp lệ của tệp Excel / CSV nhập người dùng",
)
async def preview_user_import(
    file: UploadFile = File(..., description="Tệp Excel (.xlsx, .xls) hoặc CSV (.csv)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserImportPreviewResponse:
    """
    Đọc và kiểm tra tính hợp lệ của tệp tải lên mà KHÔNG ghi vào CSDL:
    - Kiểm tra trường bắt buộc (full_name, email, role).
    - Validate định dạng email, số điện thoại Việt Nam (10 chữ số).
    - Kiểm tra trùng lặp email (trong chính file và trong CSDL với bulk lookup).
    - Phân loại rõ: NEW, EXISTING, DUPLICATE_FILE, INVALID.
    - Kiểm tra vai trò hợp lệ trên hệ thống NexusCRM.
    """
    filename = (file.filename or "").lower()
    allowed_extensions = (".xlsx", ".xls", ".csv")
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ chấp nhận tệp định dạng Excel (.xlsx, .xls) hoặc CSV (.csv).",
        )

    file_bytes = await file.read()
    raw_rows = ExcelImportService.parse_file_bytes(file_bytes, filename)
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
    summary="Thực thi nhập người dùng hàng loạt đồng bộ từ tệp hoặc JSON payload",
)
async def execute_user_import(
    request: Request,
    batch_size: int = Query(500, ge=10, le=2000, description="Kích thước lô xử lý"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserImportExecuteResponse:
    """
    Thực thi nhập dữ liệu hàng loạt:
    - Chấp nhận tệp Excel/CSV hoặc danh sách JSON payload (application/json với trường 'rows').
    - Quy tắc nghiệp vụ bắt buộc: 'Dòng lỗi bị bỏ qua, dòng hợp lệ vẫn được nhập, có báo cáo tổng kết'.
    - Tạo tài khoản với mật khẩu mặc định (Password123!) được băm bảo mật Bcrypt.
    - Tự động gán Role, Team/Department và Data Scope tương ứng (OWN / TEAM / ALL).
    - Áp dụng Batch Processing an toàn và pre-fetch cache để đạt hiệu năng cao.
    """
    content_type = request.headers.get("content-type", "").lower()
    raw_rows: List[Dict[str, Any]] = []

    if "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = form.get("file")
        if not file_obj or not hasattr(file_obj, "read"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng đính kèm tệp Excel (.xlsx) hoặc CSV (.csv) với trường 'file'.",
            )
        filename = (getattr(file_obj, "filename", "") or "").lower()
        allowed_extensions = (".xlsx", ".xls", ".csv")
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chỉ chấp nhận tệp định dạng Excel (.xlsx, .xls) hoặc CSV (.csv).",
            )
        file_bytes = await file_obj.read()
        raw_rows = ExcelImportService.parse_file_bytes(file_bytes, filename)
    else:
        try:
            body_data = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dữ liệu yêu cầu không hợp lệ. Vui lòng gửi tệp Excel/CSV hoặc JSON payload.",
            )
        if isinstance(body_data, dict):
            rows_list = body_data.get("rows") or body_data.get("users") or []
        elif isinstance(body_data, list):
            rows_list = body_data
        else:
            rows_list = []
        raw_rows = ExcelImportService.normalize_json_rows(rows_list)

    return ExcelImportService.execute_import(raw_rows, db, batch_size=batch_size)


# ==============================================================================
# BACKGROUND IMPORT JOBS (Tiến trình nhập hàng loạt chạy nền)
# ==============================================================================

def _map_job_to_response(job: UserImportJob) -> UserImportJobResponse:
    total = job.total_rows or 0
    processed = job.processed_rows or 0
    remaining = max(0, total - processed)
    return UserImportJobResponse(
        id=job.id,
        filename=job.filename,
        file_type=job.file_type,
        file_size=job.file_size or 0,
        batch_size=job.batch_size or 500,
        total_rows=total,
        processed_rows=processed,
        successful_rows=job.successful_rows or 0,
        failed_rows=job.failed_rows or 0,
        duplicate_rows=job.duplicate_rows or 0,
        remaining_rows=remaining,
        status=job.status,
        created_by_user_id=job.created_by_user_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        error_summary=job.error_summary,
    )


@router.post(
    "/jobs",
    response_model=UserImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Khởi tạo công việc nhập người dùng hàng loạt chạy nền (Background Job)",
)
async def create_import_job(
    request: Request,
    background_tasks: BackgroundTasks,
    batch_size: int = Query(500, ge=10, le=2000, description="Kích thước lô xử lý"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserImportJobResponse:
    """
    Tạo tiến trình nhập hàng loạt độc lập:
    - Trả về mã Job ID ngay lập tức (HTTP 202 Accepted).
    - Xử lý nạp dữ liệu ở chế độ chạy nền (Background Tasks), không làm nghẽn giao diện.
    - Cập nhật tiến độ xử lý và số dòng thành công/thất bại vào bảng user_import_jobs.
    - Cho phép quản trị viên rời trang và quay lại kiểm tra trạng thái bất cứ lúc nào.
    """
    content_type = request.headers.get("content-type", "").lower()
    raw_rows: List[Dict[str, Any]] = []
    filename = "users_import.json"
    file_type = "json"
    file_size = 0

    if "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = form.get("file")
        if not file_obj or not hasattr(file_obj, "read"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng đính kèm tệp Excel (.xlsx) hoặc CSV (.csv).",
            )
        filename = getattr(file_obj, "filename", "upload.xlsx") or "upload.xlsx"
        ext = filename.split(".")[-1].lower() if "." in filename else "xlsx"
        file_type = ext
        file_bytes = await file_obj.read()
        file_size = len(file_bytes)
        raw_rows = ExcelImportService.parse_file_bytes(file_bytes, filename)
    else:
        try:
            body_data = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dữ liệu yêu cầu không hợp lệ. Vui lòng gửi tệp hoặc JSON payload.",
            )
        if isinstance(body_data, dict):
            rows_list = body_data.get("rows") or body_data.get("users") or []
            if "batch_size" in body_data and isinstance(body_data["batch_size"], int):
                batch_size = body_data["batch_size"]
        elif isinstance(body_data, list):
            rows_list = body_data
        else:
            rows_list = []
        raw_rows = ExcelImportService.normalize_json_rows(rows_list)
        file_size = len(json.dumps(raw_rows).encode("utf-8"))

    if not raw_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tệp hoặc dữ liệu tải lên không có dòng dữ liệu nào để nhập.",
        )

    job = ExcelImportService.create_import_job(
        db=db,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        total_rows=len(raw_rows),
        batch_size=batch_size,
        created_by_user_id=current_user.id,
    )

    # Đưa tác vụ vào Background Tasks của FastAPI
    background_tasks.add_task(
        ExcelImportService.run_import_job_task,
        job.id,
        raw_rows,
        batch_size,
    )

    return _map_job_to_response(job)


@router.get(
    "/jobs",
    response_model=List[UserImportJobResponse],
    summary="Lấy danh sách các công việc nhập người dùng hàng loạt gần đây",
)
def list_import_jobs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> List[UserImportJobResponse]:
    """
    Lấy danh sách các tác vụ nhập hàng loạt theo thứ tự thời gian mới nhất.
    """
    jobs = (
        db.query(UserImportJob)
        .order_by(desc(UserImportJob.created_at))
        .limit(limit)
        .all()
    )
    return [_map_job_to_response(j) for j in jobs]


@router.get(
    "/jobs/{job_id}",
    response_model=UserImportJobResponse,
    summary="Xem chi tiết trạng thái và tiến độ của một công việc nhập người dùng",
)
def get_import_job_detail(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserImportJobResponse:
    """
    Truy vấn tiến độ thời gian thực của công việc nhập hàng loạt:
    - status: pending | processing | completed | failed
    - total_rows, processed_rows, successful_rows, failed_rows, duplicate_rows
    """
    job = db.query(UserImportJob).filter(UserImportJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy công việc nhập người dùng với mã ID '{job_id}'.",
        )
    return _map_job_to_response(job)


@router.get(
    "/jobs/{job_id}/errors.csv",
    summary="Tải về báo cáo danh sách dòng lỗi dạng CSV",
    response_description="Tệp CSV báo cáo lỗi",
)
def download_job_error_csv(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Xuất báo cáo các dòng dữ liệu bị lỗi kèm số thứ tự dòng, họ tên, email và lý do thất bại.
    """
    job = db.query(UserImportJob).filter(UserImportJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy công việc nhập người dùng với mã ID '{job_id}'.",
        )
    return ExcelImportService.generate_job_error_csv(job)
