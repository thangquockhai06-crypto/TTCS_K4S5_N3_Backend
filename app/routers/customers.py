from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.models.activity import Note, Activity
from app.schemas.customer import (
    CustomerDTO,
    CreateCustomerDTO,
    UpdateCustomerStatusDTO,
    CustomerNoteCreateDTO,
    CustomerActivityCreateDTO,
)
from app.services.customer_service import CustomerService
from app.core.export import export_to_excel

router = APIRouter(prefix="/customers", tags=["Customers Management"])


@router.get("", response_model=List[CustomerDTO], summary="Lấy danh sách khách hàng")
def get_customers(
    search: Optional[str] = Query(None, description="Tìm theo tên, email, sđt, công ty"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái lead/prospect/active/inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CustomerDTO]:
    customers, _ = CustomerService.get_customers(
        db=db,
        user=current_user,
        search=search,
        status=status,
        skip=skip,
        limit=limit,
    )
    return [
        CustomerDTO(
            id=c.id,
            fullName=c.full_name,
            email=c.email,
            phone=c.phone,
            company=c.company,
            status=c.status,
            healthScore=c.health_score,
            avatarUrl=c.avatar_url,
            createdAt=c.created_at.isoformat() if c.created_at else None,
        )
        for c in customers
    ]


@router.get("/export", summary="Xuất danh sách khách hàng ra Excel (.xlsx) tuân thủ Data Scope")
def export_customers(
    search: Optional[str] = Query(None, description="Tìm theo từ khóa"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Xuất danh sách khách hàng ra file Excel.
    Chỉ cho phép xuất các khách hàng nằm trong phạm vi Data Scope của người dùng hiện tại.
    """
    customers = CustomerService.get_customers_for_export(
        db=db,
        user=current_user,
        search=search,
        status=status,
    )
    headers = ["Mã KH", "Họ và tên", "Email", "Số điện thoại", "Công ty", "Trạng thái", "Điểm sức khỏe", "Ngày tạo"]
    rows = [
        [
            c.id,
            c.full_name,
            c.email,
            c.phone,
            c.company or "",
            c.status,
            c.health_score,
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


@router.post("", response_model=CustomerDTO, status_code=status.HTTP_201_CREATED, summary="Thêm mới khách hàng")
def create_customer(
    dto: CreateCustomerDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerDTO:
    c: Customer = CustomerService.create_customer(db=db, dto=dto, user=current_user)
    return CustomerDTO(
        id=c.id,
        fullName=c.full_name,
        email=c.email,
        phone=c.phone,
        company=c.company,
        status=c.status,
        healthScore=c.health_score,
        avatarUrl=c.avatar_url,
        createdAt=c.created_at.isoformat() if c.created_at else None,
    )


@router.get("/{customer_id}", response_model=CustomerDTO, summary="Xem chi tiết 360° khách hàng")
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
    return CustomerDTO(
        id=c.id,
        fullName=c.full_name,
        email=c.email,
        phone=c.phone,
        company=c.company,
        status=c.status,
        healthScore=c.health_score,
        avatarUrl=c.avatar_url,
        createdAt=c.created_at.isoformat() if c.created_at else None,
    )


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
    return CustomerDTO(
        id=c.id,
        fullName=c.full_name,
        email=c.email,
        phone=c.phone,
        company=c.company,
        status=c.status,
        healthScore=c.health_score,
        avatarUrl=c.avatar_url,
        createdAt=c.created_at.isoformat() if c.created_at else None,
    )


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
