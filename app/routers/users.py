from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserCreateSchema,
    UserUpdateSchema,
    UserResponseSchema,
    UserDeactivateSchema,
    RoleAssignSchema,
    TeamAssignSchema,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Account Management"])


@router.get("", response_model=List[UserResponseSchema], summary="Lấy danh sách người dùng")
def get_users(
    response: Response,
    search: Optional[str] = Query(None, description="Tìm kiếm theo họ tên hoặc email"),
    role: Optional[str] = Query(None, description="Lọc theo vai trò"),
    team: Optional[str] = Query(None, description="Lọc theo nhóm"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: active, inactive, locked"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[UserResponseSchema]:
    users, total_count = UserService.list_users(
        db=db,
        search=search,
        role=role,
        team=team,
        status=status,
        skip=skip,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total_count)
    return [UserResponseSchema.model_validate(u) for u in users]


@router.post("", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED, summary="Tạo mới tài khoản người dùng")
def create_user(
    payload: UserCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponseSchema:
    user: User = UserService.create_user(db=db, payload=payload, current_user=current_user)
    return UserResponseSchema.model_validate(user)


@router.get("/{user_id}", response_model=UserResponseSchema, summary="Lấy chi tiết tài khoản người dùng")
def get_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponseSchema:
    user: User = UserService.get_user_by_id(db=db, user_id=user_id)
    return UserResponseSchema.model_validate(user)


@router.put("/{user_id}", response_model=UserResponseSchema, summary="Cập nhật thông tin tài khoản người dùng")
def update_user(
    user_id: str,
    payload: UserUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponseSchema:
    updated_user: User = UserService.update_user(
        db=db,
        user_id=user_id,
        payload=payload,
        current_user=current_user,
    )
    return UserResponseSchema.model_validate(updated_user)


@router.delete("/{user_id}", summary="Xóa hoặc vô hiệu hóa tài khoản người dùng")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    return UserService.delete_user(db=db, user_id=user_id, current_user=current_user)


@router.post("/{user_id}/deactivate", summary="Vô hiệu hóa tài khoản và bàn giao toàn bộ dữ liệu")
def deactivate_user_endpoint(
    user_id: str,
    payload: UserDeactivateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return UserService.deactivate_user_and_handover(
        db=db,
        target_user_id=user_id,
        payload=payload,
        current_user=current_user,
    )


@router.post("/{user_id}/roles", response_model=UserResponseSchema, summary="Gán vai trò cho người dùng")
def assign_role_endpoint(
    user_id: str,
    payload: RoleAssignSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponseSchema:
    user: User = UserService.assign_role_endpoint(
        db=db,
        user_id=user_id,
        payload=payload,
        current_user=current_user,
    )
    return UserResponseSchema.model_validate(user)


@router.post("/{user_id}/teams", response_model=UserResponseSchema, summary="Gán nhóm cho người dùng")
def assign_team_endpoint(
    user_id: str,
    payload: TeamAssignSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponseSchema:
    user: User = UserService.assign_team_endpoint(
        db=db,
        user_id=user_id,
        payload=payload,
        current_user=current_user,
    )
    return UserResponseSchema.model_validate(user)


# ==============================================================================
# S2-01: Excel User Import Endpoint (Validate & Import)
# ==============================================================================
import re
from app.schemas.excel_import import ExcelImportPayload, ExcelImportResultDTO, InvalidRowDetail
from app.core.security import get_password_hash

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
VN_PHONE_REGEX = re.compile(r"^(03|05|07|08|09)\d{8}$")


@router.post("/import-excel", response_model=ExcelImportResultDTO, summary="Nhập người dùng từ Excel / JSON có kiểm tra hợp lệ (S2-01)")
def import_users_excel(
    payload: ExcelImportPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExcelImportResultDTO:
    """
    Import hàng loạt người dùng từ file Excel / danh sách dòng:
    - Kiểm tra email hợp lệ & không trùng lặp (CSDL và trong cùng file).
    - Dòng không hợp lệ được đánh dấu rõ nguyên nhân và KHÔNG nạp vào CSDL.
    - Dòng hợp lệ được thêm vào hệ thống an toàn.
    """
    total = len(payload.rows)
    failed_rows: List[InvalidRowDetail] = []
    inserted_users: List[Dict[str, Any]] = []
    seen_emails = set()

    for idx, row in enumerate(payload.rows):
        row_num = idx + 1
        name = (row.name or "").strip()
        email = (row.email or "").strip().lower()

        # 1. Validate Tên
        if not name:
            failed_rows.append(InvalidRowDetail(
                row_index=row_num,
                data=row.model_dump(),
                error="Họ và tên không được để trống.",
            ))
            continue

        # 2. Validate Định dạng Email
        if not email or not EMAIL_REGEX.match(email):
            failed_rows.append(InvalidRowDetail(
                row_index=row_num,
                data=row.model_dump(),
                error=f"Email '{email}' không đúng định dạng.",
            ))
            continue

        # 3. Validate Trùng trong file import
        if email in seen_emails:
            failed_rows.append(InvalidRowDetail(
                row_index=row_num,
                data=row.model_dump(),
                error=f"Email '{email}' bị trùng lặp trong danh sách nhập.",
            ))
            continue
        seen_emails.add(email)

        # 4. Validate Trùng với CSDL hiện có
        existing_in_db = db.query(User).filter(User.email == email).first()
        if existing_in_db:
            failed_rows.append(InvalidRowDetail(
                row_index=row_num,
                data=row.model_dump(),
                error=f"Email '{email}' đã tồn tại trên hệ thống CRM.",
            ))
            continue

        # 5. Validate Số điện thoại (nếu có)
        phone = (row.phone or "").strip().replace(" ", "").replace("-", "") if row.phone else None
        if phone and not VN_PHONE_REGEX.match(phone):
            failed_rows.append(InvalidRowDetail(
                row_index=row_num,
                data=row.model_dump(),
                error=f"Số điện thoại '{row.phone}' không đúng định dạng di động Việt Nam (10 chữ số).",
            ))
            continue

        # 6. Insert dòng hợp lệ
        new_user = User(
            email=email,
            password_hash=get_password_hash("NexusCRM@2026"),
            full_name=name,
            role=row.role or "Account Executive",
            title="Chuyên viên Kinh doanh",
            department=row.group or "Kinh doanh",
            status="active",
        )
        db.add(new_user)
        inserted_users.append({
            "name": name,
            "email": email,
            "role": new_user.role,
        })

    db.commit()

    return ExcelImportResultDTO(
        total=total,
        success_count=len(inserted_users),
        failed_count=len(failed_rows),
        failed_rows=failed_rows,
        inserted_users=inserted_users,
    )


# ==============================================================================
# S2-02: User Profile Update Endpoint (Vietnamese Phone & Read-only Role/Email)
# ==============================================================================
from pydantic import BaseModel

class UserProfileUpdateDTO(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    avatar_url: Optional[str] = None


@router.put("/me/profile", response_model=UserResponseSchema, summary="Cập nhật hồ sơ cá nhân (S2-02)")
def update_my_profile(
    dto: UserProfileUpdateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponseSchema:
    """
    Cập nhật thông tin cá nhân:
    - Kiểm tra số điện thoại chuẩn Việt Nam (10 số, 03/05/07/08/09).
    - Email và Role luôn bị vô hiệu hóa / chỉ đọc, không thể tự chỉnh sửa.
    """
    if dto.phone:
        cleaned_phone = dto.phone.strip().replace(" ", "").replace("-", "")
        if not VN_PHONE_REGEX.match(cleaned_phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Số điện thoại không đúng định dạng Việt Nam (10 chữ số, bắt đầu bằng 03, 05, 07, 08, 09).",
            )

    if dto.full_name is not None and dto.full_name.strip():
        current_user.full_name = dto.full_name.strip()
    if dto.title is not None:
        current_user.title = dto.title.strip()
    if dto.department is not None:
        current_user.department = dto.department.strip()
    if dto.avatar_url is not None:
        current_user.avatar_url = dto.avatar_url.strip()

    db.commit()
    db.refresh(current_user)
    return UserResponseSchema.model_validate(current_user)
