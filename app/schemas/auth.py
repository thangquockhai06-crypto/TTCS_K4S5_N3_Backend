from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class LoginPayload(BaseModel):
    email: str
    password: str
    rememberMe: Optional[bool] = False

class RegisterPayload(BaseModel):
    fullName: str
    email: str
    companyName: Optional[str] = "NexusCRM Enterprise VN"
    roleTitle: Optional[str] = "Account Executive"
    password: str
    confirmPassword: Optional[str] = None

class RefreshTokenPayload(BaseModel):
    refreshToken: str

class UserDTO(BaseModel):
    id: str
    fullName: str = Field(..., serialization_alias="fullName")
    email: str
    role: str
    title: str
    department: str
    avatarUrl: Optional[str] = Field(None, serialization_alias="avatarUrl")
    avatarThumbnailUrl: Optional[str] = Field(None, serialization_alias="avatarThumbnailUrl")
    workspaceName: str = Field(..., serialization_alias="workspaceName")
    teamId: Optional[str] = Field(None, serialization_alias="teamId")
    dataScope: Optional[str] = Field(None, serialization_alias="dataScope")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class AuthResponse(BaseModel):
    accessToken: str = Field(..., serialization_alias="accessToken")
    refreshToken: str = Field(..., serialization_alias="refreshToken")
    expiresIn: int = Field(..., serialization_alias="expiresIn")
    tokenType: str = Field("Bearer", serialization_alias="tokenType")
    user: UserDTO
    issuedAt: str = Field(..., serialization_alias="issuedAt")

    model_config = ConfigDict(populate_by_name=True)

class RefreshTokenResponseDTO(BaseModel):
    accessToken: str = Field(..., serialization_alias="accessToken")
    refreshToken: str = Field(..., serialization_alias="refreshToken")
    expiresIn: int = Field(..., serialization_alias="expiresIn")
    refreshedAt: str = Field(..., serialization_alias="refreshedAt")

    model_config = ConfigDict(populate_by_name=True)

class MessageResponse(BaseModel):
    message: str
    retryAfterSeconds: Optional[int] = None

class ForgotPasswordPayload(BaseModel):
    email: str

class ResetPasswordPayload(BaseModel):
    token: str
    newPassword: str = Field(..., alias="new_password")

    model_config = ConfigDict(populate_by_name=True)

class ChangePasswordPayload(BaseModel):
    currentPassword: str = Field(..., alias="current_password")
    newPassword: str = Field(..., alias="new_password")
    currentRefreshToken: Optional[str] = Field(None, alias="current_refresh_token")

    model_config = ConfigDict(populate_by_name=True)


