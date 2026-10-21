"""
Pydantic v2 Schemas cho tính năng Nhập danh sách khách hàng hàng loạt từ Excel (SCRUM-64 / S3-06).
Bao gồm:
- CustomerImportRow: Thông tin một dòng import (kèm cờ validate, lỗi và trùng lặp).
- CustomerImportPreviewResponse: Kết quả xem trước dữ liệu (dry-run preview).
- CustomerImportExecuteRequest: Yêu cầu thực thi nhập dữ liệu kèm tùy chọn duplicate_action.
- CustomerImportSummaryResponse: Báo cáo kết quả tổng kết sau khi thực thi.
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class CustomerImportRow(BaseModel):
    """
    Đại diện cho một bản ghi khách hàng trong tệp Excel/CSV cần import.
    """
    model_config = ConfigDict(from_attributes=True)

    row_number: int = Field(..., description="Số thứ tự dòng trong tệp (bắt đầu từ 2)")
    name: str = Field(..., description="Tên khách hàng / doanh nghiệp (bắt buộc, từ 2 đến 150 ký tự)")
    tax_code: Optional[str] = Field(None, description="Mã số thuế (10 hoặc 13 chữ số)")
    email: Optional[str] = Field(None, description="Địa chỉ email liên hệ")
    phone: Optional[str] = Field(None, description="Số điện thoại liên hệ")
    website: Optional[str] = Field(None, description="Địa chỉ website / tên miền")
    address: Optional[str] = Field(None, description="Địa chỉ trụ sở / văn phòng")
    status: Optional[str] = Field("LEAD", description="Trạng thái khách hàng: LEAD, CONTACTED, CUSTOMER")
    is_valid: bool = Field(True, description="Trạng thái hợp lệ dữ liệu của dòng")
    errors: List[str] = Field(default_factory=list, description="Danh sách chi tiết các lỗi validation của dòng")
    is_duplicate: bool = Field(False, description="Cờ đánh dấu trùng lặp với CSDL hoặc trong file")
    duplicate_reason: Optional[str] = Field(None, description="Lý do và thông tin đối soát trùng lặp")
    matched_customer_id: Optional[str] = Field(None, description="ID khách hàng đã tồn tại trùng khớp")
    matched_customer_name: Optional[str] = Field(None, description="Tên khách hàng đã tồn tại trùng khớp")


class CustomerImportPreviewResponse(BaseModel):
    """
    Kết quả xem trước (dry-run preview) tệp import khách hàng.
    """
    model_config = ConfigDict(from_attributes=True)

    total_rows: int = Field(..., description="Tổng số dòng dữ liệu đọc được từ tệp")
    valid_rows_count: int = Field(..., description="Số dòng dữ liệu hợp lệ (sẵn sàng import)")
    invalid_rows_count: int = Field(..., description="Số dòng dữ liệu không hợp lệ (có lỗi)")
    duplicate_rows_count: int = Field(..., description="Số dòng dữ liệu bị trùng lặp")
    rows: List[CustomerImportRow] = Field(..., description="Danh sách chi tiết từng dòng dữ liệu và trạng thái")


class CustomerImportExecuteRequest(BaseModel):
    """
    Yêu cầu thực thi nhập dữ liệu khách hàng vào CSDL.
    """
    model_config = ConfigDict(from_attributes=True)

    duplicate_action: Literal["SKIP", "UPDATE"] = Field(
        "SKIP",
        description="Hành động xử lý bản ghi trùng lặp: 'SKIP' (bỏ qua không ghi đè), 'UPDATE' (cập nhật thông tin mới)"
    )
    rows: List[CustomerImportRow] = Field(..., description="Danh sách các dòng cần nhập")


class CustomerImportSummaryResponse(BaseModel):
    """
    Báo cáo kết quả tổng kết sau khi thực thi nhập dữ liệu hàng loạt.
    """
    model_config = ConfigDict(from_attributes=True)

    total_rows: int = Field(..., description="Tổng số dòng được gửi lên xử lý")
    imported_count: int = Field(..., description="Số khách hàng mới được tạo thành công")
    updated_count: int = Field(..., description="Số khách hàng trùng lặp được cập nhật thông tin")
    skipped_count: int = Field(..., description="Số bản ghi trùng lặp bị bỏ qua")
    failed_count: int = Field(..., description="Số dòng bị lỗi validation không import được")
    errors_detail: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Danh sách chi tiết các dòng không import được kèm lý do"
    )
