"""
Pydantic Schemas cho phân hệ Quản lý Tài khoản người dùng (User Management CRUD).
Tuân thủ PEP 8, Pydantic v2 và 100% Type Hints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBaseSchema(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150, alias="fullName", description="Họ và tên người dùng")
    email: EmailStr = Field(..., description="Địa chỉ email công ty (bắt buộc duy nhất)")
    role: Optional[str] = Field("Account Executive", description="Tên vai trò hệ thống")
    team_id: Optional[str] = Field(None, alias="teamId", description="Mã nhóm kinh doanh")
    title: Optional[str] = Field(None, description="Chức danh")
    department: Optional[str] = Field(None, description="Phòng ban")
    status: Optional[str] = Field("active", description="Trạng thái tài khoản (active, inactive, locked)")

    model_config = ConfigDict(populate_by_name=True)


class UserCreateSchema(UserBaseSchema):
    role_id: Optional[str] = Field(None, alias="roleId", description="Mã ID vai trò từ bảng roles (nếu có)")


class UserUpdateSchema(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150, alias="fullName", description="Họ và tên")
    title: Optional[str] = Field(None, description="Chức danh")
    department: Optional[str] = Field(None, description="Phòng ban")
    role: Optional[str] = Field(None, description="Vai trò")
    role_id: Optional[str] = Field(None, alias="roleId", description="Mã vai trò")
    team_id: Optional[str] = Field(None, alias="teamId", description="Mã nhóm")
    status: Optional[str] = Field(None, description="Trạng thái tài khoản")

    model_config = ConfigDict(populate_by_name=True)


class UserResponseSchema(BaseModel):
    id: str = Field(..., description="Mã định danh người dùng")
    full_name: str = Field(..., serialization_alias="fullName")
    email: str = Field(..., description="Email")
    role: str = Field(..., description="Vai trò chính")
    team_id: Optional[str] = Field(None, serialization_alias="teamId")
    status: str = Field("active", description="Trạng thái tài khoản")
    title: Optional[str] = Field(None, description="Chức danh")
    department: Optional[str] = Field(None, description="Phòng ban")
    avatar_url: Optional[str] = Field(None, serialization_alias="avatarUrl")
    workspace_name: Optional[str] = Field("NexusCRM Enterprise VN", serialization_alias="workspaceName")
    created_at: Optional[datetime] = Field(None, serialization_alias="createdAt")
    updated_at: Optional[datetime] = Field(None, serialization_alias="updatedAt")

    # Đảm bảo KHÔNG BAO GIỜ để lộ password_hash
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class UserDeactivateSchema(BaseModel):
    successor_user_id: str = Field(..., min_length=1, alias="successorUserId", description="Mã ID người kế thừa nhận bàn giao dữ liệu")
    reason: Optional[str] = Field("Bàn giao công việc và khóa tài khoản", description="Lý do khóa tài khoản")

    model_config = ConfigDict(populate_by_name=True)


class RoleAssignSchema(BaseModel):
    role_id: Optional[str] = Field(None, alias="roleId", description="ID vai trò")
    role_name: Optional[str] = Field(None, alias="roleName", description="Tên vai trò")

    model_config = ConfigDict(populate_by_name=True)


class TeamAssignSchema(BaseModel):
    team_id: Optional[str] = Field(None, alias="teamId", description="ID nhóm")
    team_name: Optional[str] = Field(None, alias="teamName", description="Tên nhóm")

    model_config = ConfigDict(populate_by_name=True)
