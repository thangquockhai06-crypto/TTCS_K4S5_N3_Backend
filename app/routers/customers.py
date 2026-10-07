from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.models.activity import Note, Activity
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.support_ticket import SupportTicket
from app.schemas.customer import (
    CustomerDTO,
    CreateCustomerDTO,
    UpdateCustomerDTO,
    UpdateCustomerStatusDTO,
    CustomerNoteCreateDTO,
    CustomerActivityCreateDTO,
    CustomerMergeDTO,
    CustomerHierarchyDTO,
    StagnantCustomerDTO,
    RiskScanResultDTO,
)
from app.schemas.customer_360 import Customer360DTO
from app.services.customer_service import CustomerService
from app.services.customer_360_service import Customer360Service
from app.services.customer_merge_service import CustomerMergeService
from app.services.corporate_hierarchy_service import CorporateHierarchyService
from app.services.customer_excel_import_service import CustomerExcelImportService
from app.services.support_ticket_service import SupportTicketService
from app.core.export import export_to_excel

router = APIRouter(prefix="/customers", tags=["Customers Management"])


def _to_customer_dto(c: Customer, db: Optional[Session] = None) -> CustomerDTO:
    contacts_count = 0
    deals_count = 0
    open_tickets_count = 0
    if db:
        contacts_count = db.query(Contact).filter(Contact.customer_id == c.id).count()
        deals_count = db.query(Deal).filter(Deal.customer_id == c.id).count()
        open_tickets_count = (
            db.query(SupportTicket)
            .filter(
                SupportTicket.customer_id == c.id,
                SupportTicket.status.in_(["open", "in_progress"]),
            )
            .count()
        )

    return CustomerDTO(
        id=c.id,
        fullName=c.full_name,
        email=c.email,
        phone=c.phone,
        company=c.company,
        status=c.status,
        healthScore=c.health_score,
        avatarUrl=c.avatar_url,
        taxCode=c.tax_code,
        parentCustomerId=c.parent_customer_id,
        totalContractValue=float(c.total_contract_value or 0.0),
        lastInteractionAt=c.last_interaction_at.isoformat() if c.last_interaction_at else None,
        riskFlag=bool(c.risk_flag),
        riskReason=c.risk_reason,
        industry=c.industry,
        tier=c.tier,
        location=c.location,
        website=c.website,
        notesSummary=c.notes_summary,
        assignedUserId=c.assigned_user_id,
        ownerName=c.assigned_user.full_name if c.assigned_user else None,
        createdAt=c.created_at.isoformat() if c.created_at else None,
        updatedAt=c.updated_at.isoformat() if c.updated_at else None,
        contactsCount=contacts_count,
        dealsCount=deals_count,
        openTicketsCount=open_tickets_count,
    )


@router.get("", response_model=List[CustomerDTO], summary="Lấy danh sách khách hàng có bộ lọc nâng cao (S3-01, S3-07)")
def get_customers(
    search: Optional[str] = Query(None, description="Tìm theo tên, email, sđt, công ty, MST"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái lead/prospect/active/inactive/negotiation"),
    industry: Optional[str] = Query(None, description="Lọc theo lĩnh vực/ngành nghề"),
    tier: Optional[str] = Query(None, description="Lọc theo phân khúc Enterprise/Mid-Market/Startup"),
    owner_id: Optional[str] = Query(None, description="Lọc theo nhân viên phụ trách"),
    risk_only: Optional[bool] = Query(None, description="Chỉ lấy khách hàng có cờ rủi ro"),
    min_value: Optional[float] = Query(None, description="Giá trị hợp đồng tối thiểu"),
    max_value: Optional[float] = Query(None, description="Giá trị hợp đồng tối đa"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CustomerDTO]:
    customers, _ = CustomerService.get_customers(
        db=db,
        user=current_user,
        search=search,
        status=status,
        industry=industry,
        tier=tier,
        owner_id=owner_id,
        risk_only=risk_only,
        min_value=min_value,
        max_value=max_value,
        skip=skip,
        limit=limit,
    )
    return [_to_customer_dto(c, db) for c in customers]


@router.get("/stagnant", response_model=List[StagnantCustomerDTO], summary="Danh sách cần chăm sóc định kỳ (S3-09)")
def get_stagnant_customers(
    days: int = Query(30, ge=1, description="Số ngày không có tương tác"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[StagnantCustomerDTO]:
    customers = CustomerService.get_stagnant_customers(
        db=db,
        user=current_user,
        days=days,
        limit=limit,
    )
    from datetime import datetime
    now = datetime.utcnow()
    result = []
    for c in customers:
        days_inactive = 999
        if c.last_interaction_at:
            delta = now - c.last_interaction_at
            days_inactive = max(0, delta.days)

        result.append(
            StagnantCustomerDTO(
                id=c.id,
                fullName=c.full_name,
                company=c.company or c.full_name,
                phone=c.phone,
                email=c.email,
                status=c.status,
                ownerName=c.assigned_user.full_name if c.assigned_user else "Chưa gán",
                lastInteractionAt=c.last_interaction_at.isoformat() if c.last_interaction_at else None,
                daysInactive=days_inactive,
                totalContractValue=float(c.total_contract_value or 0.0),
                riskFlag=bool(c.risk_flag),
            )
        )
    return result


@router.get("/duplicates", summary="Tìm danh sách khách hàng có nguy cơ trùng lặp (S3-04)")
def get_potential_duplicates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    pairs = CustomerMergeService.find_potential_duplicates(db=db, user=current_user)
    return [
        {
            "reason": p["reason"],
            "customerA": _to_customer_dto(p["customerA"], db),
            "customerB": _to_customer_dto(p["customerB"], db),
        }
        for p in pairs
    ]


@router.post("/merge", response_model=CustomerDTO, summary="Gộp khách hàng trùng lặp (S3-04)")
def merge_customers(
    dto: CustomerMergeDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerDTO:
    master = CustomerMergeService.merge_customers(
        db=db,
        master_id=dto.masterId,
        duplicate_id=dto.duplicateId,
        user=current_user,
        field_overrides=dto.fieldOverrides,
    )
    return _to_customer_dto(master, db)


@router.post("/import-preview", summary="Xem trước file Excel nhập khách hàng (S3-06)")
async def preview_excel_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    return CustomerExcelImportService.validate_and_preview(db=db, file_content=content, user=current_user)


@router.post("/import", summary="Nhập khách hàng từ Excel với Bulk Upsert (S3-06)")
async def import_customers_from_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    return CustomerExcelImportService.execute_import(db=db, file_content=content, user=current_user)


@router.post("/scan-risks", response_model=RiskScanResultDTO, summary="Kích hoạt quét cờ rủi ro tự động (S3-08)")
def trigger_risk_scan(
    threshold: int = Query(2, ge=1, description="Số ticket quá hạn cảnh báo rủi ro"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskScanResultDTO:
    scan_res = SupportTicketService.scan_and_update_all_risks(db=db, threshold=threshold)
    return RiskScanResultDTO(
        scannedCount=scan_res["scannedCount"],
        flaggedCount=scan_res["flaggedCount"],
        threshold=scan_res["threshold"],
        details=scan_res["details"],
    )


@router.get("/export", summary="Xuất danh sách khách hàng ra Excel (.xlsx) tuân thủ Data Scope")
def export_customers(
    search: Optional[str] = Query(None, description="Tìm theo từ khóa"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customers = CustomerService.get_customers_for_export(
        db=db,
        user=current_user,
        search=search,
        status=status,
    )
    headers = ["Mã KH", "Họ và tên", "Email", "Số điện thoại", "Công ty", "Mã số thuế", "Trạng thái", "Giá trị hợp đồng", "Ngày tạo"]
    rows = [
        [
            c.id,
            c.full_name,
            c.email,
            c.phone,
            c.company or "",
            c.tax_code or "",
            c.status,
            float(c.total_contract_value or 0.0),
            c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
        ]
        for c in customers
    ]
    return export_to_excel(
        sheet_title="KhachHang",
        headers=headers,
        rows=rows,
        filename="danh_sach_khach_hang.xlsx",
    )


@router.post("", response_model=CustomerDTO, status_code=status.HTTP_201_CREATED, summary="Thêm mới khách hàng doanh nghiệp (S3-01)")
def create_customer(
    dto: CreateCustomerDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerDTO:
    c: Customer = CustomerService.create_customer(db=db, dto=dto, user=current_user)
    return _to_customer_dto(c, db)


@router.get("/{customer_id}", response_model=CustomerDTO, summary="Xem chi tiết hồ sơ khách hàng (S3-01)")
def get_customer_detail(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerDTO:
    c: Optional[Customer] = CustomerService.get_customer_by_id(
        db=db,
        customer_id=customer_id,
        user=current_user,
    )
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khách hàng.")
    return _to_customer_dto(c, db)


@router.put("/{customer_id}", response_model=CustomerDTO, summary="Cập nhật hồ sơ khách hàng (S3-01)")
def update_customer(
    customer_id: str,
    dto: UpdateCustomerDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerDTO:
    c = CustomerService.update_customer(
        db=db,
        customer_id=customer_id,
        dto=dto,
        user=current_user,
    )
    return _to_customer_dto(c, db)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa mềm khách hàng (S3-01)")
def delete_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    CustomerService.delete_customer(
        db=db,
        customer_id=customer_id,
        user=current_user,
    )
    return None


@router.get("/{customer_id}/360", response_model=Customer360DTO, summary="Khách hàng 360° View (S3-03)")
def get_customer_360_view(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Customer360DTO:
    return Customer360Service.get_customer_360(
        db=db,
        customer_id=customer_id,
        user=current_user,
    )


@router.get("/{customer_id}/hierarchy", response_model=CustomerHierarchyDTO, summary="Cây phân cấp công ty Mẹ - Con (S3-05)")
def get_corporate_hierarchy(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerHierarchyDTO:
    return CorporateHierarchyService.get_hierarchy(
        db=db,
        customer_id=customer_id,
        user=current_user,
    )


@router.put("/{customer_id}/parent", response_model=CustomerDTO, summary="Thiết lập công ty mẹ (S3-05)")
def set_parent_customer(
    customer_id: str,
    parent_id: Optional[str] = Query(None, description="ID của công ty mẹ (để trống nếu muốn hủy liên kết mẹ)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerDTO:
    c = CorporateHierarchyService.set_parent(
        db=db,
        customer_id=customer_id,
        parent_id=parent_id,
        user=current_user,
    )
    return _to_customer_dto(c, db)


@router.post("/{customer_id}/quick-touch", response_model=CustomerDTO, summary="Hành động nhanh 'Đã liên hệ' (S3-09)")
def quick_touch_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerDTO:
    c = CustomerService.quick_touch(
        db=db,
        customer_id=customer_id,
        user=current_user,
    )
    return _to_customer_dto(c, db)


@router.get("/{customer_id}/risk", summary="Kiểm tra trạng thái cờ rủi ro (S3-08)")
def get_customer_risk_status(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = CustomerService.get_customer_by_id(db=db, customer_id=customer_id, user=current_user)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khách hàng.")
    return {
        "customerId": c.id,
        "riskFlag": bool(c.risk_flag),
        "riskReason": c.risk_reason,
    }


@router.patch("/{customer_id}/status", response_model=CustomerDTO, summary="Cập nhật trạng thái khách hàng")
def update_status(
    customer_id: str,
    dto: UpdateCustomerStatusDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerDTO:
    c: Optional[Customer] = CustomerService.update_status(
        db=db,
        customer_id=customer_id,
        new_status=dto.status,
        user=current_user,
    )
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khách hàng.")
    return _to_customer_dto(c, db)


@router.post("/{customer_id}/notes", summary="Thêm ghi chú cho khách hàng")
def add_note(
    customer_id: str,
    dto: CustomerNoteCreateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    note: Note = CustomerService.add_note(
        db=db,
        customer_id=customer_id,
        content=dto.content,
        user=current_user,
    )
    return {"ok": True, "noteId": note.id, "createdAt": note.created_at.isoformat()}


@router.post("/{customer_id}/activities", summary="Ghi nhận hoạt động liên hệ")
def add_activity(
    customer_id: str,
    dto: CustomerActivityCreateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    activity: Activity = CustomerService.add_activity(
        db=db,
        customer_id=customer_id,
        activity_type=dto.type,
        title=dto.title,
        description=dto.description or "",
        user=current_user,
    )
    return {"ok": True, "activityId": activity.id, "createdAt": activity.created_at.isoformat()}
