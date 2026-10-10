from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ExcelImportUserRow(BaseModel):
    name: str
    email: str
    role: Optional[str] = "sales"
    group: Optional[str] = "Miền Bắc (Hà Nội)"
    phone: Optional[str] = None


class ExcelImportPayload(BaseModel):
    rows: List[ExcelImportUserRow]


class InvalidRowDetail(BaseModel):
    row_index: int
    data: Dict[str, Any]
    error: str


class ExcelImportResultDTO(BaseModel):
    total: int
    success_count: int
    failed_count: int
    failed_rows: List[InvalidRowDetail]
    inserted_users: List[Dict[str, Any]]


# ==============================================================================
# SCRUM-79 / SCRUM-123 BE: Schemas for Template, Preview, and Execute Import
# ==============================================================================

class ImportRowDetail(BaseModel):
    row_index: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    status: str  # "VALID" hoặc "INVALID"
    classification: Optional[str] = "NEW"  # "NEW", "EXISTING", "DUPLICATE_FILE", "INVALID"
    errors: List[str] = []


class UserImportPreviewResponse(BaseModel):
    total_rows: int
    valid_count: int
    error_count: int
    details: List[ImportRowDetail]


class ImportedUserSummary(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    department: Optional[str] = None
    data_scope: Optional[str] = None


class FailedRowSummary(BaseModel):
    row_index: int
    email: Optional[str] = None
    full_name: Optional[str] = None
    errors: List[str]


class UserImportExecuteResponse(BaseModel):
    total_rows: int
    imported_count: int
    failed_count: int
    imported_users: List[ImportedUserSummary]
    failed_rows: List[FailedRowSummary]


class UserImportExecutePayload(BaseModel):
    rows: Optional[List[Dict[str, Any]]] = None


class UserImportJobResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    batch_size: int
    total_rows: int
    processed_rows: int
    successful_rows: int
    failed_rows: int
    duplicate_rows: int
    remaining_rows: int
    status: str  # "pending", "processing", "completed", "failed"
    created_by_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_summary: Optional[str] = None


class UserImportJobCreatePayload(BaseModel):
    batch_size: Optional[int] = 500
    rows: Optional[List[Dict[str, Any]]] = None

