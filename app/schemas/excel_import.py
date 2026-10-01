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
