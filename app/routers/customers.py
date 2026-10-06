from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User
from app.models.customer import Customer
from app.models.activity import Note, Activity
from app.schemas.customer import (
    CustomerDTO,
    AssignedUserDTO,
    ContactDTO,
    CreateCustomerDTO,
    UpdateCustomerStatusDTO,
    CustomerNoteCreateDTO,
    CustomerActivityCreateDTO,
)
from app.schemas.customer_merge import (
    DuplicateCheckRequest,
    DuplicateMatchItem,
    CustomerCompareResponse,
    CustomerMergeRequest,
    CustomerMergeResponse,
)
from app.services.customer_service import CustomerService
from app.services.customer_search_service import CustomerSearchService
from app.services.customer_merge_service import CustomerMergeService
from app.core.export import export_to_excel


router = APIRouter(prefix="/customers", tags=["Customers Management"])


def _to_customer_dto(customer: Customer, include_contacts: bool = True) -> CustomerDTO:
    assigned_user = customer.assigned_user
    assigned_user_dto = (
        AssignedUserDTO(
            id=assigned_user.id,
            fullName=assigned_user.full_name,
            avatarThumbnailUrl=assigned_user.avatar_thumbnail_url,
        )
        if assigned_user
        else None
    )
    def contact_dto(contact) -> ContactDTO:
        return ContactDTO(
            id=contact.id,
            fullName=contact.full_name,
            phone=contact.phone,
            email=contact.email,
            isPrimary=bool(contact.is_primary),
        )

    contacts = [contact_dto(contact) for contact in customer.contacts] if include_contacts else []
    primary_contact = contact_dto(customer.contacts[0]) if customer.contacts else None
    return CustomerDTO(
        id=customer.id,
        fullName=customer.full_name,
        email=customer.email,
        phone=customer.phone,
        company=customer.company,
        status=customer.status,
        healthScore=customer.health_score,
        industry=customer.industry,
        companySize=customer.company_size,
        region=customer.region,
        taxCode=customer.tax_code,
        website=customer.website,
        assignedUserId=customer.assigned_user_id,
        assignedUser=assigned_user_dto,
        avatarUrl=customer.avatar_url,
        contacts=contacts,
        primaryContact=primary_contact,
        createdAt=customer.created_at.isoformat() if customer.created_at else None,
    )


@router.get("", response_model=List[CustomerDTO], summary="Lấy danh sách khách hàng")
def get_customers(
    q: Optional[str] = Query(None, description="Tìm theo tên, mã số thuế hoặc số điện thoại"),
    search: Optional[str] = Query(None, description="Tương thích ngược với tham số search"),
    status_values: Optional[List[str]] = Query(None, alias="status"),
    industries: Optional[List[str]] = Query(None, alias="industry"),
    company_sizes: Optional[List[str]] = Query(None, alias="companySize"),
    regions: Optional[List[str]] = Query(None, alias="region"),
    owners: Optional[List[str]] = Query(None, alias="owner"),
    sort: Optional[str] = Query(None),
    descending: Optional[bool] = Query(None),
    saved_filter_id: Optional[str] = Query(None, alias="saved_filter_id"),
    skip: Optional[int] = Query(None, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=200),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, alias="pageSize", ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,
) -> List[CustomerDTO]:
    if page is not None:
        limit = page_size or limit or 50
        skip = (page - 1) * limit
    elif page_size is not None:
        limit = page_size

    customers, total = CustomerSearchService(db).list_customers(
        user=current_user,
        saved_filter_id=saved_filter_id,
        q=q if q is not None else search,
        status_values=status_values,
        industries=industries,
        company_sizes=company_sizes,
        regions=regions,
        owners=owners,
        sort=sort,
        descending=descending,
        skip=skip,
        limit=limit,
    )
    if response is not None:
        response.headers["X-Total-Count"] = str(total)
    return [_to_customer_dto(customer, include_contacts=False) for customer in customers]


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
    return _to_customer_dto(c)


@router.post(
    "/duplicates/scan",
    response_model=List[DuplicateMatchItem],
    summary="Quét và phát hiện khách hàng trùng lặp đa tiêu chí (SCRUM-62)",
)
def scan_customer_duplicates(
    dto: DuplicateCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DuplicateMatchItem]:
    """
    Phát hiện các khách hàng trùng lặp theo:
    - Mã số thuế (tax_code)
    - Website domain
    - Tên công ty / họ tên (Fuzzy string matching >= 80%)
    - Số điện thoại liên hệ
    """
    return CustomerMergeService.scan_duplicates(db=db, request=dto, current_user=current_user)


@router.get(
    "/compare",
    response_model=CustomerCompareResponse,
    summary="So sánh chi tiết hai khách hàng cạnh nhau trước khi gộp (SCRUM-62)",
)
def compare_customers(
    primary_id: str = Query(..., description="ID khách hàng chính (Master/Target)"),
    duplicate_id: str = Query(..., description="ID khách hàng phụ cần gộp (Duplicate/Source)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerCompareResponse:
    """
    Trả về toàn bộ dữ liệu của hai bản ghi song song (hồ sơ, contacts, deals, activities)
    kèm danh sách các trường có sự khác biệt để người dùng đối chiếu trước khi gộp.
    """
    return CustomerMergeService.compare_customers(
        db=db,
        primary_id=primary_id,
        duplicate_id=duplicate_id,
        current_user=current_user,
    )


@router.post(
    "/merge",
    response_model=CustomerMergeResponse,
    summary="Thực hiện gộp khách hàng trong một DB Transaction an toàn (SCRUM-62)",
)
def merge_customers(
    dto: CustomerMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["TEAM_LEAD", "DIRECTOR"])),
) -> CustomerMergeResponse:
    """
    Chỉ dành cho Trưởng nhóm kinh doanh (TEAM_LEAD) trở lên (DIRECTOR / ADMIN).
    Bảo toàn toàn bộ người liên hệ, cơ hội bán hàng và lịch sử hoạt động sang bản ghi chính.
    Bản ghi phụ được đánh dấu là đã gộp (is_deleted = True, merged_into_id = target_id).
    Ghi nhận lịch sử Activity trên bản ghi chính.
    """
    return CustomerMergeService.merge_customers(db=db, request=dto, current_user=current_user)


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
    return _to_customer_dto(c)


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
    return _to_customer_dto(c)


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
