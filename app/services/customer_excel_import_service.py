import io
import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import validate_vietnamese_mst


class CustomerExcelImportService:
    """
    Service nhập dữ liệu khách hàng từ file Excel (.xlsx / .xls) S3-06.
    - Hỗ trợ phân tích (Parse), xác thực (Validate), xem trước (Preview).
    - So sánh Mã số thuế (MST) đối soát với CSDL.
    - Bulk Upsert: Tự động cập nhật nếu đã tồn tại MST, thêm mới nếu chưa có.
    - Trả về báo cáo thống kê chi tiết, loại trừ lỗi và trùng lặp.
    """

    REQUIRED_COLUMNS = ["full_name", "company", "phone", "email"]

    COLUMN_MAPPINGS = {
        "họ và tên": "full_name",
        "tên khách hàng": "full_name",
        "họ tên": "full_name",
        "người đại diện": "full_name",
        "full_name": "full_name",
        "tên công ty": "company",
        "doanh nghiệp": "company",
        "công ty": "company",
        "company": "company",
        "số điện thoại": "phone",
        "sđt": "phone",
        "điện thoại": "phone",
        "phone": "phone",
        "email": "email",
        "thư điện tử": "email",
        "mã số thuế": "tax_code",
        "mst": "tax_code",
        "tax_code": "tax_code",
        "lĩnh vực": "industry",
        "ngành nghề": "industry",
        "industry": "industry",
        "phân khúc": "tier",
        "tier": "tier",
        "địa chỉ": "location",
        "location": "location",
        "website": "website",
        "trạng thái": "status",
        "status": "status",
        "giá trị hợp đồng": "total_contract_value",
        "doanh số": "total_contract_value",
        "contract_value": "total_contract_value",
    }

    @classmethod
    def _normalize_headers(cls, df: pd.DataFrame) -> pd.DataFrame:
        normalized_cols = []
        for col in df.columns:
            cleaned = str(col).strip().lower()
            mapped = cls.COLUMN_MAPPINGS.get(cleaned, cleaned)
            normalized_cols.append(mapped)
        df.columns = normalized_cols
        return df

    @classmethod
    def parse_excel_to_rows(cls, file_content: bytes) -> List[Dict[str, Any]]:
        """Đọc và chuẩn hóa nội dung file Excel thành danh sách bản ghi."""
        df = pd.read_excel(io.BytesIO(file_content), dtype=str)
        df = df.fillna("")
        df = cls._normalize_headers(df)
        rows: List[Dict[str, Any]] = []
        for idx, r in df.iterrows():
            row_dict = {k: str(v).strip() for k, v in r.to_dict().items()}
            row_dict["_row_number"] = idx + 2  # Dòng thực tế trong file Excel (1-indexed + header)
            rows.append(row_dict)
        return rows

    @classmethod
    def validate_and_preview(
        cls,
        db: Session,
        file_content: bytes,
        user: User,
    ) -> Dict[str, Any]:
        """
        Phân tích sơ bộ và trả về danh sách bản ghi xem trước (Preview)
        kèm trạng thái lỗi hoặc trùng lặp MST.
        """
        rows = cls.parse_excel_to_rows(file_content)

        preview_items: List[Dict[str, Any]] = []
        seen_mst_in_file: Dict[str, int] = {}
        total = len(rows)
        valid_count = 0
        invalid_count = 0
        duplicate_mst_count = 0

        for r in rows:
            row_num = r.get("_row_number", 0)
            errors: List[str] = []
            is_duplicate_mst = False

            # 1. Kiểm tra trường bắt buộc
            full_name = r.get("full_name", "")
            company = r.get("company", "")
            phone = r.get("phone", "")
            email = r.get("email", "")
            tax_code = r.get("tax_code", "")

            if not full_name:
                errors.append("Thiếu họ tên khách hàng")
            if not company:
                errors.append("Thiếu tên công ty/doanh nghiệp")
            if not phone:
                errors.append("Thiếu số điện thoại")
            elif len(phone) < 7:
                errors.append("Số điện thoại không hợp lệ")

            if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                errors.append("Định dạng email không hợp lệ")

            # 2. Kiểm tra định dạng và trùng lặp MST
            if tax_code:
                try:
                    cleaned_mst = validate_vietnamese_mst(tax_code)
                    r["tax_code"] = cleaned_mst
                    # Kiểm tra trùng trong cùng file
                    if cleaned_mst in seen_mst_in_file:
                        errors.append(f"Trùng MST với dòng {seen_mst_in_file[cleaned_mst]} trong file")
                        is_duplicate_mst = True
                        duplicate_mst_count += 1
                    else:
                        seen_mst_in_file[cleaned_mst] = row_num

                    # Kiểm tra tồn tại trong CSDL (để báo sẽ cập nhật hay thêm mới)
                    existing_db = CustomerRepository.get_by_tax_code(db, cleaned_mst)
                    if existing_db:
                        r["_action"] = "UPDATE"
                        r["_existing_id"] = existing_db.id
                    else:
                        r["_action"] = "INSERT"
                except ValueError as ve:
                    errors.append(str(ve))
            else:
                r["_action"] = "INSERT"

            is_valid = len(errors) == 0
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1

            preview_items.append({
                "rowNumber": row_num,
                "fullName": full_name,
                "company": company,
                "phone": phone,
                "email": email,
                "taxCode": tax_code,
                "industry": r.get("industry", ""),
                "tier": r.get("tier", "Enterprise"),
                "totalContractValue": float(r.get("total_contract_value", 0.0) or 0.0),
                "action": r.get("_action", "INSERT"),
                "isValid": is_valid,
                "isDuplicateMST": is_duplicate_mst,
                "errors": errors,
            })

        return {
            "totalRows": total,
            "validRows": valid_count,
            "invalidRows": invalid_count,
            "duplicateRows": duplicate_mst_count,
            "previewItems": preview_items,
        }

    @classmethod
    def execute_import(
        cls,
        db: Session,
        file_content: bytes,
        user: User,
    ) -> Dict[str, Any]:
        """
        Thực hiện nhập dữ liệu hàng loạt vào CSDL (Bulk Upsert).
        - Nếu bản ghi hợp lệ và chưa có MST: Thêm mới (INSERT).
        - Nếu đã có MST trong CSDL: Cập nhật thông tin (UPDATE).
        - Bản ghi lỗi được bỏ qua và liệt kê chi tiết trong danh sách lỗi.
        """
        preview_data = cls.validate_and_preview(db, file_content, user)
        preview_items = preview_data["previewItems"]

        imported_count = 0
        updated_count = 0
        skipped_count = 0
        errors_list: List[Dict[str, Any]] = []

        for item in preview_items:
            if not item["isValid"]:
                skipped_count += 1
                errors_list.append({
                    "rowNumber": item["rowNumber"],
                    "company": item["company"],
                    "taxCode": item["taxCode"],
                    "reasons": item["errors"],
                })
                continue

            mst = item["taxCode"] or None
            existing_customer = CustomerRepository.get_by_tax_code(db, mst) if mst else None

            if existing_customer:
                # Cập nhật thông tin khách hàng hiện tại (UPDATE)
                existing_customer.full_name = item["fullName"] or existing_customer.full_name
                existing_customer.phone = item["phone"] or existing_customer.phone
                if item["email"]:
                    existing_customer.email = item["email"]
                if item["industry"]:
                    existing_customer.industry = item["industry"]
                if item["tier"]:
                    existing_customer.tier = item["tier"]
                if item["totalContractValue"] > 0:
                    existing_customer.total_contract_value = item["totalContractValue"]
                existing_customer.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # Thêm mới khách hàng (INSERT)
                new_cust = Customer(
                    id=str(uuid.uuid4()),
                    full_name=item["fullName"],
                    email=item["email"] or f"{uuid.uuid4().hex[:6]}@domain.vn",
                    phone=item["phone"],
                    company=item["company"],
                    tax_code=mst,
                    industry=item["industry"] or "Công nghệ & Dịch vụ",
                    tier=item["tier"] or "Enterprise",
                    total_contract_value=item["totalContractValue"] or 0.0,
                    status="lead",
                    health_score=85,
                    assigned_user_id=user.id,
                    avatar_url=f"https://api.dicebear.com/7.x/initials/svg?seed={item['fullName']}",
                    last_interaction_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                )
                db.add(new_cust)
                imported_count += 1

        db.commit()

        return {
            "totalRows": preview_data["totalRows"],
            "validRows": preview_data["validRows"],
            "invalidRows": preview_data["invalidRows"],
            "duplicateRows": preview_data["duplicateRows"],
            "importedRows": imported_count,
            "updatedRows": updated_count,
            "skippedRows": skipped_count,
            "errors": errors_list,
        }
