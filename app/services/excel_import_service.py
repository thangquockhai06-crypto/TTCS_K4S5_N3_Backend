"""
Tầng Service xử lý nghiệp vụ Nhập Người Dùng Hàng Loạt từ Excel (SCRUM-79 / SCRUM-123 BE).
Bao gồm:
- Tạo và tải tệp Excel mẫu (.xlsx).
- Xem trước (Preview) và kiểm tra tính hợp lệ dữ liệu (Validation).
- Thực thi nhập hàng loạt (Execute Import) bỏ qua dòng lỗi, nạp dòng hợp lệ có transaction an toàn.
Tuân thủ PEP 8, 100% Type Hints và Clean Layered Architecture.
"""
import io
import re
import uuid
from typing import List, Dict, Any, Tuple, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.user import User
from app.core.security import hash_password
from app.core.scope import ROLE_SCOPE_MAPPING, DataScope
from app.repositories.user_repository import UserRepository
from app.schemas.excel_import import (
    ImportRowDetail,
    UserImportPreviewResponse,
    ImportedUserSummary,
    FailedRowSummary,
    UserImportExecuteResponse,
)

# Regex chuẩn cho Email và Số điện thoại Việt Nam
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
VN_PHONE_REGEX = re.compile(r"^(?:0|\+84)(3|5|7|8|9)\d{8}$")

# Danh mục các vai trò được phép trên hệ thống NexusCRM
VALID_ROLES = {
    "super admin", "admin", "quản trị viên", "sales director", "vp of sales",
    "director", "giám đốc kinh doanh", "sales manager", "team leader", "trưởng nhóm",
    "revops lead", "account executive", "sales rep", "sales", "nhân viên kinh doanh",
    "nhân viên", "employee", "manager", "lead"
}


class ExcelImportService:
    """
    Service quản lý toàn bộ quy trình Excel User Import.
    """

    @staticmethod
    def generate_template() -> StreamingResponse:
        """
        Sinh file Excel mẫu (.xlsx) chuẩn gồm 5 cột:
        full_name, email, phone, role, department
        Kèm 2 dòng dữ liệu mẫu và định dạng chuyên nghiệp.
        """
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "User_Import_Template"

        headers = ["full_name", "email", "phone", "role", "department"]
        sample_rows = [
            [
                "Nguyễn Văn A",
                "nguyenvana@nexuscrm.vn",
                "0912345678",
                "Account Executive",
                "Phòng Kinh Doanh Miền Bắc",
            ],
            [
                "Trần Thị B",
                "tranthib@nexuscrm.vn",
                "0987654321",
                "Sales Manager",
                "Phòng Kinh Doanh Miền Nam",
            ],
        ]

        # Style header
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style="thin", color="D3D3D3"),
            right=Side(style="thin", color="D3D3D3"),
            top=Side(style="thin", color="D3D3D3"),
            bottom=Side(style="thin", color="D3D3D3"),
        )

        worksheet.row_dimensions[1].height = 28
        worksheet.append(headers)

        for col_idx in range(1, len(headers) + 1):
            cell = worksheet.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        # Chèn dữ liệu mẫu
        data_font = Font(name="Arial", size=10)
        data_align = Alignment(vertical="center")

        for row_data in sample_rows:
            worksheet.append(row_data)

        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row, min_col=1, max_col=len(headers)):
            worksheet.row_dimensions[row[0].row].height = 22
            for cell in row:
                cell.font = data_font
                cell.alignment = data_align
                cell.border = thin_border

        # Tự động điều chỉnh độ rộng cột
        for col in worksheet.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            worksheet.column_dimensions[col_letter].width = max(max_len + 5, 20)

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)

        response_headers = {
            "Content-Disposition": 'attachment; filename="users_import_template.xlsx"',
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=response_headers,
        )

    @staticmethod
    def parse_excel_bytes(file_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Đọc tệp Excel (.xlsx) từ bytes và chuẩn hóa danh sách các dòng dữ liệu.
        Hỗ trợ ánh xạ tên cột linh hoạt (tiếng Việt & tiếng Anh).
        """
        try:
            workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tệp tải lên không phải là tệp Excel (.xlsx) hợp lệ hoặc tệp bị hỏng: {str(exc)}",
            )

        worksheet = workbook.active
        if not worksheet or worksheet.max_row < 2:
            return []

        # Đọc tiêu đề dòng 1
        header_cells = [cell.value for cell in worksheet[1]]
        col_map: Dict[str, int] = {}

        header_aliases = {
            "full_name": {"full_name", "fullname", "họ và tên", "họ tên", "ho ten", "name", "tên", "ten", "ho_ten"},
            "email": {"email", "mail", "thư điện tử", "thu dien tu"},
            "phone": {"phone", "số điện thoại", "điện thoại", "so dien thoai", "so_dien_thoai", "sdt"},
            "role": {"role", "vai trò", "chức vụ", "vai tro", "vai_tro", "chuc vu"},
            "department": {"department", "phòng ban", "nhóm", "team", "group", "phong ban", "phong_ban", "nhom"},
        }

        for idx, h in enumerate(header_cells):
            if not h:
                continue
            norm_h = str(h).strip().lower()
            for key, aliases in header_aliases.items():
                if norm_h in aliases and key not in col_map:
                    col_map[key] = idx
                    break

        # Dự phòng vị trí mặc định nếu tiêu đề không khớp
        if "full_name" not in col_map and len(header_cells) >= 1:
            col_map["full_name"] = 0
        if "email" not in col_map and len(header_cells) >= 2:
            col_map["email"] = 1
        if "phone" not in col_map and len(header_cells) >= 3:
            col_map["phone"] = 2
        if "role" not in col_map and len(header_cells) >= 4:
            col_map["role"] = 3
        if "department" not in col_map and len(header_cells) >= 5:
            col_map["department"] = 4

        raw_rows: List[Dict[str, Any]] = []

        for row_idx, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
            # Bỏ qua dòng trống hoàn toàn
            if all(v is None or str(v).strip() == "" for v in row):
                continue

            def get_val(key: str) -> Optional[str]:
                idx = col_map.get(key)
                if idx is not None and idx < len(row):
                    val = row[idx]
                    if val is not None:
                        # Xử lý trường hợp số điện thoại dạng int/float
                        if isinstance(val, float) and val.is_integer():
                            val = int(val)
                        s = str(val).strip()
                        return s if s else None
                return None

            raw_rows.append({
                "row_index": row_idx,
                "full_name": get_val("full_name"),
                "email": get_val("email"),
                "phone": get_val("phone"),
                "role": get_val("role"),
                "department": get_val("department"),
            })

        return raw_rows

    @staticmethod
    def normalize_json_rows(rows_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chuẩn hóa danh sách dòng từ JSON payload sang cấu trúc thống nhất.
        """
        normalized: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows_data, start=1):
            full_name = row.get("full_name") or row.get("name")
            email = row.get("email")
            phone = row.get("phone")
            role = row.get("role")
            department = row.get("department") or row.get("group") or row.get("team")

            normalized.append({
                "row_index": row.get("row_index", idx),
                "full_name": str(full_name).strip() if full_name else None,
                "email": str(email).strip() if email else None,
                "phone": str(phone).strip() if phone else None,
                "role": str(role).strip() if role else None,
                "department": str(department).strip() if department else None,
            })
        return normalized

    @classmethod
    def validate_rows(
        cls,
        rows: List[Dict[str, Any]],
        db: Session,
    ) -> Tuple[List[ImportRowDetail], int, int]:
        """
        Kiểm tra tính hợp lệ của từng dòng theo quy tắc nghiệp vụ:
        - Không để trống họ tên, email, vai trò (role).
        - Định dạng email hợp lệ.
        - Không trùng lặp email trong file và không tồn tại trong CSDL.
        - Định dạng số điện thoại chuẩn Việt Nam (nếu có).
        - Vai trò phải thuộc danh mục hợp lệ trên hệ thống.
        """
        details: List[ImportRowDetail] = []
        seen_emails: set = set()
        valid_count = 0
        error_count = 0

        for row in rows:
            row_idx = row.get("row_index", 1)
            full_name = row.get("full_name")
            email = row.get("email")
            phone = row.get("phone")
            role = row.get("role")
            department = row.get("department")

            row_errors: List[str] = []

            # 1. Kiểm tra Họ và tên
            if not full_name:
                row_errors.append("Họ và tên không được để trống.")

            # 2. Kiểm tra Email
            if not email:
                row_errors.append("Email không được để trống.")
            else:
                norm_email = email.lower()
                if not EMAIL_REGEX.match(norm_email):
                    row_errors.append(f"Email '{email}' không đúng định dạng.")
                elif norm_email in seen_emails:
                    row_errors.append(f"Email '{email}' bị trùng lặp trong tệp Excel.")
                else:
                    seen_emails.add(norm_email)
                    existing_user = db.query(User).filter(User.email == norm_email).first()
                    if existing_user:
                        row_errors.append(f"Email '{email}' đã tồn tại trên hệ thống CRM.")

            # 3. Kiểm tra Vai trò (Role)
            if not role:
                row_errors.append("Vai trò (Role) không được để trống.")
            else:
                if role.lower() not in VALID_ROLES:
                    row_errors.append(f"Vai trò '{role}' không hợp lệ trên hệ thống NexusCRM.")

            # 4. Kiểm tra Số điện thoại (nếu có)
            if phone:
                clean_phone = re.sub(r"[\s\-\.]", "", str(phone))
                if clean_phone.startswith("+84"):
                    clean_phone = "0" + clean_phone[3:]
                elif clean_phone.startswith("84") and len(clean_phone) == 11:
                    clean_phone = "0" + clean_phone[2:]

                if not VN_PHONE_REGEX.match(clean_phone):
                    row_errors.append(
                        f"Số điện thoại '{phone}' không đúng định dạng di động Việt Nam (10 chữ số)."
                    )

            if row_errors:
                status_str = "INVALID"
                error_count += 1
            else:
                status_str = "VALID"
                valid_count += 1

            details.append(
                ImportRowDetail(
                    row_index=row_idx,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    role=role,
                    department=department,
                    status=status_str,
                    errors=row_errors,
                )
            )

        return details, valid_count, error_count

    @classmethod
    def execute_import(
        cls,
        rows: List[Dict[str, Any]],
        db: Session,
    ) -> UserImportExecuteResponse:
        """
        Thực thi nhập dữ liệu hàng loạt:
        - Bỏ qua các dòng lỗi (Failed rows).
        - Nhập các dòng hợp lệ vào CSDL với transaction an toàn.
        - Hash mật khẩu mặc định bằng Bcrypt.
        - Gán Role, Team/Department và Data Scope tương ứng.
        - Trả về báo cáo tổng kết chi tiết.
        """
        details, valid_count, error_count = cls.validate_rows(rows, db)

        imported_users: List[ImportedUserSummary] = []
        failed_rows: List[FailedRowSummary] = []

        default_pwd_hash = hash_password("Password123!")

        try:
            for item in details:
                if item.status == "INVALID":
                    failed_rows.append(
                        FailedRowSummary(
                            row_index=item.row_index,
                            email=item.email,
                            full_name=item.full_name,
                            errors=item.errors,
                        )
                    )
                    continue

                # Xử lý dòng VALID
                email = item.email.strip().lower()
                full_name = item.full_name.strip()
                role_name = item.role.strip()
                department = item.department.strip() if item.department else None

                # Ánh xạ Data Scope từ Role
                role_key = role_name.lower()
                scope_enum = ROLE_SCOPE_MAPPING.get(role_key, DataScope.OWN)
                data_scope_val = scope_enum.value

                # Lấy hoặc tạo Role & Team
                role_obj = UserRepository.get_or_create_role(db, role_name)
                team_obj = UserRepository.get_or_create_team(db, department) if department else None

                new_user = User(
                    id=str(uuid.uuid4()),
                    email=email,
                    password_hash=default_pwd_hash,
                    full_name=full_name,
                    role=role_obj.name,
                    title=f"Chuyên viên {department}" if department else "Nhân viên kinh doanh",
                    department=department or "Phòng Kinh Doanh",
                    team_id=team_obj.id if team_obj else None,
                    data_scope=data_scope_val,
                    status="active",
                )
                db.add(new_user)

                # Gán liên kết bảng trung gian
                UserRepository.assign_role_to_user(db, new_user, role_obj)
                if team_obj:
                    UserRepository.assign_team_to_user(db, new_user, team_obj)

                imported_users.append(
                    ImportedUserSummary(
                        id=new_user.id,
                        full_name=new_user.full_name,
                        email=new_user.email,
                        role=new_user.role,
                        department=new_user.department,
                        data_scope=new_user.data_scope,
                    )
                )

            db.commit()

        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi hệ thống khi lưu dữ liệu người dùng: {str(exc)}",
            )

        return UserImportExecuteResponse(
            total_rows=len(rows),
            imported_count=len(imported_users),
            failed_count=len(failed_rows),
            imported_users=imported_users,
            failed_rows=failed_rows,
        )
