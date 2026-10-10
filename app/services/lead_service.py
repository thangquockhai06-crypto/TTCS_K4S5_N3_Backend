"""
LeadService: Tầng xử lý nghiệp vụ Khách hàng tiềm năng (SCRUM-40 / Sprint 4).
Hỗ trợ:
- Tạo thủ công 1 Lead (bắt buộc có nguồn - Lead Source Requirement).
- Tải tệp Excel mẫu chuẩn (.xlsx) với openpyxl.
- Xem trước (preview/dry-run) và kiểm tra lỗi từng dòng (row-by-row validation).
- Thực thi nhập dữ liệu hàng loạt theo Transaction an toàn.
"""
import io
import csv
import re
import uuid
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import StreamingResponse

from app.models.lead import Lead
from app.models.user import User
from app.schemas.lead_import import (
    LeadCreateManualRequest,
    LeadResponse,
    LeadImportRowValidation,
    LeadImportPreviewResponse,
    LeadImportExecuteRequest,
    LeadImportExecuteResponse,
    clean_phone_number,
    VN_PHONE_REGEX,
)

# Email Regex chuẩn
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Header Synonyms hỗ trợ đọc file Excel / CSV linh hoạt cả tiếng Việt và tiếng Anh
HEADER_SYNONYMS: Dict[str, str] = {
    # Họ và tên
    "full_name": "full_name",
    "fullname": "full_name",
    "name": "full_name",
    "họ và tên": "full_name",
    "ho va ten": "full_name",
    "họ tên": "full_name",
    "ho ten": "full_name",
    "tên": "full_name",
    "ten": "full_name",
    "tên lead": "full_name",
    "khách hàng": "full_name",
    "khach hang": "full_name",
    # Số điện thoại
    "phone": "phone",
    "telephone": "phone",
    "mobile": "phone",
    "cell": "phone",
    "sđt": "phone",
    "sdt": "phone",
    "số điện thoại": "phone",
    "so dien thoai": "phone",
    "điện thoại": "phone",
    "dien thoai": "phone",
    # Email
    "email": "email",
    "e-mail": "email",
    "mail": "email",
    "hòm thư": "email",
    "hom thu": "email",
    # Công ty
    "company": "company",
    "công ty": "company",
    "cong ty": "company",
    "doanh nghiệp": "company",
    "doanh nghiep": "company",
    "tên công ty": "company",
    "ten cong ty": "company",
    # Nhu cầu quan tâm
    "interest_need": "interest_need",
    "interest": "interest_need",
    "need": "interest_need",
    "nhu cầu quan tâm": "interest_need",
    "nhu cau quan tam": "interest_need",
    "nhu cầu": "interest_need",
    "nhu cau": "interest_need",
    "quan tâm": "interest_need",
    "quan tam": "interest_need",
    # Nguồn lead (BẮT BUỘC)
    "source": "source",
    "lead_source": "source",
    "lead source": "source",
    "nguồn lead": "source",
    "nguon lead": "source",
    "nguồn": "source",
    "nguon": "source",
    # Ghi chú
    "notes": "notes",
    "note": "notes",
    "ghi chú": "notes",
    "ghi chu": "notes",
    "mô tả": "notes",
    "mo ta": "notes",
}


def normalize_header(raw_header: Any) -> Optional[str]:
    """Chuẩn hóa tiêu đề cột sang trường dữ liệu hệ thống."""
    if not raw_header:
        return None
    cleaned = str(raw_header).strip().lower()
    # Loại bỏ dấu ngoặc chú thích nếu có, ví dụ: 'Họ và tên (*)' -> 'họ và tên'
    cleaned = re.sub(r"\s*[\(\[].*?[\)\]]", "", cleaned).strip()
    return HEADER_SYNONYMS.get(cleaned)


class LeadService:
    @staticmethod
    def create_manual_lead(db: Session, request: LeadCreateManualRequest, current_user: User) -> Lead:
        """
        Tạo mới một Lead thủ công từ sự kiện hoặc danh thiếp.
        AC:
        - BẮT BUỘC có nguồn (source).
        - Trạng thái mặc định: status = 'NEW'.
        - Gắn created_by = current_user.id.
        """
        source_val = (request.source or "").strip()
        if not source_val:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Mọi lead nhập vào đều bắt buộc phải có nguồn (source).",
            )

        lead = Lead(
            id=str(uuid.uuid4()),
            full_name=request.full_name.strip(),
            phone=clean_phone_number(request.phone),
            email=str(request.email).strip().lower() if request.email else None,
            company=request.company.strip() if request.company else None,
            interest_need=request.interest_need.strip() if request.interest_need else None,
            source=source_val,
            notes=request.notes.strip() if request.notes else None,
            status="NEW",
            created_by=current_user.id,
            campaign_id=request.campaign_id,
        )

        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def generate_template() -> StreamingResponse:
        """
        Tạo và trả về tệp Excel mẫu (.xlsx) chuẩn gồm các cột:
        full_name, phone, email, company, interest_need, source, notes
        kèm 2-3 dòng dữ liệu mẫu minh họa.
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "DanhSachLead"

        headers = [
            "Họ và tên (*)",
            "Số điện thoại (*)",
            "Email",
            "Công ty",
            "Nhu cầu quan tâm",
            "Nguồn lead (*)",
            "Ghi chú",
        ]
        ws.append(headers)

        # Style header
        header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        ws.row_dimensions[1].height = 28
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = thin_border

        # Dữ liệu mẫu minh họa
        sample_rows = [
            [
                "Nguyễn Văn An",
                "0912345678",
                "an.nguyen@alpha.vn",
                "Công ty Cổ phần Công nghệ Alpha",
                "Giải pháp CRM Doanh nghiệp",
                "Hội thảo",
                "Gặp tại Hội thảo Chuyển đổi số 2026",
            ],
            [
                "Trần Thị Bình",
                "0987654321",
                "binh.tran@betagroup.com",
                "Tập đoàn Bán lẻ Beta",
                "Phần mềm quản lý bán hàng B2B",
                "Danh thiếp",
                "Nhận danh thiếp tại triển lãm công nghệ",
            ],
            [
                "Lê Hoàng Cường",
                "0905123456",
                "cuong.le@gammacorp.vn",
                "Công ty TNHH Sản xuất Gamma",
                "Tích hợp đa kênh Omnichannel",
                "Sự kiện",
                "Khách tham quan gian hàng hội chợ xúc tiến thương mại",
            ],
        ]

        data_font = Font(name="Calibri", size=10)
        data_alignment = Alignment(vertical="center")

        for row_idx, row_data in enumerate(sample_rows, start=2):
            ws.append(row_data)
            ws.row_dimensions[row_idx].height = 22
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = data_font
                cell.alignment = data_alignment
                cell.border = thin_border

        # Tự căn chỉnh độ rộng cột
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or "")
                max_len = max(max_len, len(val))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="lead_import_template.xlsx"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )

    @staticmethod
    def _parse_file_rows(file: UploadFile, content: bytes) -> Tuple[List[str], List[List[Any]]]:
        """Đọc tệp Excel (.xlsx, .xls) hoặc CSV (.csv) thành header và rows."""
        filename = (file.filename or "").lower()

        if filename.endswith(".csv"):
            text_content = None
            for enc in ["utf-8-sig", "utf-8", "utf-16", "latin-1"]:
                try:
                    text_content = content.decode(enc)
                    break
                except Exception:
                    continue
            if text_content is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể giải mã tệp CSV. Vui lòng đảm bảo tệp lưu định dạng UTF-8.",
                )
            reader = csv.reader(io.StringIO(text_content))
            raw_rows = list(reader)
            if not raw_rows:
                return [], []
            headers = [str(c).strip() for c in raw_rows[0]]
            data_rows = raw_rows[1:]
            return headers, data_rows

        elif filename.endswith((".xlsx", ".xls")):
            try:
                wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tệp Excel không hợp lệ hoặc bị lỗi cấu trúc: {str(e)}",
                )
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)
            try:
                header_row = next(rows_iter)
            except StopIteration:
                return [], []
            headers = [str(c).strip() if c is not None else "" for c in header_row]
            data_rows = [list(r) for r in rows_iter]
            return headers, data_rows
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Định dạng tệp không được hỗ trợ. Vui lòng tải lên tệp .xlsx, .xls hoặc .csv.",
            )

    @classmethod
    async def preview_import(
        cls,
        file: UploadFile,
        db: Session,
        current_user: User,
    ) -> LeadImportPreviewResponse:
        """
        Đọc và kiểm tra tính hợp lệ của tệp Excel/CSV tải lên (dry-run preview):
        - Validate từng dòng (Row-by-row):
          * Bắt buộc có: full_name (2-150 ký tự), phone (chuẩn VN), source (BẮT BUỘC THEO AC).
          * Email: đúng định dạng nếu có.
        - Quét trùng lặp sơ bộ:
          * Trùng lặp nội bộ trong file (theo phone và email).
          * Trùng lặp với CSDL hiện có (theo phone và email).
        - Trả về danh sách chi tiết kèm row_number, is_valid, errors.
        """
        # Giới hạn kích thước tệp tối đa 10MB
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kích thước tệp vượt quá giới hạn cho phép (Tối đa 10MB).",
            )

        headers, data_rows = cls._parse_file_rows(file, content)
        if not headers or not data_rows:
            return LeadImportPreviewResponse(
                total_rows=0,
                valid_count=0,
                invalid_count=0,
                preview_rows=[],
            )

        # Ánh xạ chỉ số cột theo tiêu đề đã chuẩn hóa
        col_map: Dict[str, int] = {}
        for idx, h in enumerate(headers):
            field_name = normalize_header(h)
            if field_name and field_name not in col_map:
                col_map[field_name] = idx

        # Lấy trước danh sách SĐT và Email đã có trong CSDL để đối soát nhanh
        existing_leads = db.query(Lead.phone, Lead.email).all()
        db_phones: Set[str] = {clean_phone_number(l.phone) for l in existing_leads if l.phone}
        db_emails: Set[str] = {l.email.strip().lower() for l in existing_leads if l.email}

        preview_rows: List[LeadImportRowValidation] = []
        seen_phones_in_file: Dict[str, int] = {}
        seen_emails_in_file: Dict[str, int] = {}

        row_idx = 1  # Dòng 1 là tiêu đề
        for row in data_rows:
            row_idx += 1
            # Bỏ qua dòng trống hoàn toàn
            if not any(cell is not None and str(cell).strip() != "" for cell in row):
                continue

            def get_val(f_name: str) -> Optional[str]:
                col_i = col_map.get(f_name)
                if col_i is not None and col_i < len(row):
                    val = row[col_i]
                    if val is not None:
                        s = str(val).strip()
                        return s if s else None
                return None

            raw_name = get_val("full_name")
            raw_phone = get_val("phone")
            raw_email = get_val("email")
            raw_company = get_val("company")
            raw_interest = get_val("interest_need")
            raw_source = get_val("source")
            raw_notes = get_val("notes")

            errors: List[str] = []

            # 1. Kiểm tra nguồn (source) - BẮT BUỘC THEO AC
            if not raw_source:
                errors.append("Nguồn lead (source) là bắt buộc.")

            # 2. Kiểm tra Họ và tên (full_name)
            if not raw_name:
                errors.append("Họ và tên là bắt buộc.")
            elif len(raw_name) < 2:
                errors.append("Họ và tên tối thiểu 2 ký tự.")
            elif len(raw_name) > 150:
                errors.append("Họ và tên không được vượt quá 150 ký tự.")

            # 3. Kiểm tra Số điện thoại (phone)
            cleaned_phone = ""
            if not raw_phone:
                errors.append("Số điện thoại là bắt buộc.")
            else:
                cleaned_phone = clean_phone_number(raw_phone)
                if not VN_PHONE_REGEX.match(cleaned_phone):
                    errors.append("Số điện thoại không đúng định dạng Việt Nam (10 chữ số, ví dụ: 0912345678).")

            # 4. Kiểm tra Email (nếu có)
            norm_email = ""
            if raw_email:
                norm_email = raw_email.lower().strip()
                if not EMAIL_REGEX.match(norm_email):
                    errors.append("Email không đúng định dạng (ví dụ: example@domain.com).")

            # 5. Kiểm tra trùng lặp nội bộ trong file
            if cleaned_phone and VN_PHONE_REGEX.match(cleaned_phone):
                if cleaned_phone in seen_phones_in_file:
                    errors.append(f"Số điện thoại trùng lặp với dòng {seen_phones_in_file[cleaned_phone]} trong tệp.")
                else:
                    seen_phones_in_file[cleaned_phone] = row_idx

            if norm_email and EMAIL_REGEX.match(norm_email):
                if norm_email in seen_emails_in_file:
                    errors.append(f"Email trùng lặp với dòng {seen_emails_in_file[norm_email]} trong tệp.")
                else:
                    seen_emails_in_file[norm_email] = row_idx

            # 6. Kiểm tra trùng lặp với CSDL
            if cleaned_phone and cleaned_phone in db_phones:
                errors.append("Số điện thoại đã tồn tại trên hệ thống.")

            if norm_email and norm_email in db_emails:
                errors.append("Email đã tồn tại trên hệ thống.")

            is_valid = len(errors) == 0

            preview_rows.append(
                LeadImportRowValidation(
                    row_number=row_idx,
                    full_name=raw_name,
                    phone=raw_phone,
                    email=raw_email,
                    company=raw_company,
                    interest_need=raw_interest,
                    source=raw_source,
                    notes=raw_notes,
                    is_valid=is_valid,
                    errors=errors,
                )
            )

        valid_count = sum(1 for r in preview_rows if r.is_valid)
        invalid_count = sum(1 for r in preview_rows if not r.is_valid)

        return LeadImportPreviewResponse(
            total_rows=len(preview_rows),
            valid_count=valid_count,
            invalid_count=invalid_count,
            preview_rows=preview_rows,
        )

    @classmethod
    def execute_import(
        cls,
        db: Session,
        request: LeadImportExecuteRequest,
        current_user: User,
    ) -> LeadImportExecuteResponse:
        """
        Thực thi nhập dữ liệu Lead vào CSDL theo Transaction:
        - Chỉ nạp các dòng hợp lệ, bỏ qua các dòng lỗi (nếu skip_errors=True).
        - Gắn created_by = current_user.id, status = 'NEW'.
        - Thực hiện trong Transaction an toàn (rollback khi có lỗi hệ thống).
        """
        rows = request.rows or []
        if not rows:
            return LeadImportExecuteResponse(
                total_rows=0,
                imported_count=0,
                failed_count=0,
                details=[],
            )

        imported_count = 0
        failed_count = 0
        details: List[Dict[str, Any]] = []

        try:
            for row in rows:
                # Nếu dòng không hợp lệ
                if not row.is_valid:
                    failed_count += 1
                    details.append({
                        "row_number": row.row_number,
                        "status": "FAILED",
                        "errors": row.errors or ["Dữ liệu dòng không hợp lệ"],
                    })
                    continue

                # Kiểm tra lại điều kiện bắt buộc source
                source_val = (row.source or "").strip()
                if not source_val:
                    failed_count += 1
                    details.append({
                        "row_number": row.row_number,
                        "status": "FAILED",
                        "errors": ["Nguồn lead (source) là bắt buộc"],
                    })
                    continue

                cleaned_phone = clean_phone_number(row.phone or "")
                if not cleaned_phone:
                    failed_count += 1
                    details.append({
                        "row_number": row.row_number,
                        "status": "FAILED",
                        "errors": ["Số điện thoại là bắt buộc"],
                    })
                    continue

                lead = Lead(
                    id=str(uuid.uuid4()),
                    full_name=(row.full_name or "").strip(),
                    phone=cleaned_phone,
                    email=row.email.strip().lower() if row.email else None,
                    company=row.company.strip() if row.company else None,
                    interest_need=row.interest_need.strip() if row.interest_need else None,
                    source=source_val,
                    notes=row.notes.strip() if row.notes else None,
                    status="NEW",
                    created_by=current_user.id,
                    campaign_id=row.campaign_id or request.campaign_id,
                )
                db.add(lead)
                imported_count += 1
                details.append({
                    "row_number": row.row_number,
                    "status": "SUCCESS",
                    "id": lead.id,
                    "phone": lead.phone,
                })

            db.commit()
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi transaction khi lưu dữ liệu import: {str(exc)}",
            )

        return LeadImportExecuteResponse(
            total_rows=len(rows),
            imported_count=imported_count,
            failed_count=failed_count,
            details=details,
        )
