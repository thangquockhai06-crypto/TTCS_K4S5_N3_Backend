from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


def format_file_size(size_bytes: int) -> str:
    """Định dạng kích thước tệp thành chuỗi dễ đọc (B, KB, MB)."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} B"


class UploaderInfoSchema(BaseModel):
    """Thông tin người tải tài liệu lên."""
    id: str
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class DealAttachmentResponse(BaseModel):
    """Schema phản hồi thông tin tệp tài liệu đính kèm (SCRUM-208)."""
    id: str
    deal_id: str
    original_filename: str
    content_type: Optional[str] = None
    file_size: int
    file_size_formatted: str
    uploaded_by: str
    uploader: Optional[UploaderInfoSchema] = None
    created_at: datetime
    download_url: str

    model_config = ConfigDict(from_attributes=True)


class DealAttachmentListResponse(BaseModel):
    """Schema danh sách tài liệu đính kèm của cơ hội (SCRUM-208)."""
    deal_id: str
    total_files: int
    total_size_bytes: int
    items: List[DealAttachmentResponse]

    model_config = ConfigDict(from_attributes=True)
