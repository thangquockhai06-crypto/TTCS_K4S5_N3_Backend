"""
Bộ kiểm thử tự động cho SCRUM-72 / S1-04: Đổi mật khẩu khi đang đăng nhập (FastAPI Backend).
- POST /api/v1/auth/change-password
- Bắt buộc kiểm tra verify mật khẩu cũ
- Validate mật khẩu mới (tối thiểu 8 ký tự, có chữ và số)
- Thu hồi tất cả các phiên đăng nhập khác
"""
import os
import sys

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token



@pytest.fixture
def auth_header_and_user(client: TestClient, db_session: Session):
    """Tạo người dùng mẫu và Access Token để test endpoint yêu cầu đăng nhập."""
    user = User(
        id="test-cp-01",
        full_name="Nguyễn Văn ChangePass",
        email="change_pass_user@nexuscrm.vn",
        password_hash=hash_password("OldPassword123!"),
        role="staff",
        status="active",
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user


def test_change_password_success(client: TestClient, db_session: Session, auth_header_and_user):
    """
    [SCRUM-72 / S1-04] Test đổi mật khẩu thành công khi nhập đúng mật khẩu cũ và mật khẩu mới hợp lệ.
    """
    headers, user = auth_header_and_user

    response = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "OldPassword123!",
            "new_password": "BrandNewSecurePassword2026!",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Đổi mật khẩu thành công" in data["message"]

    # Kiểm tra CSDL đã cập nhật mật khẩu mới
    db_session.refresh(user)
    assert verify_password("BrandNewSecurePassword2026!", user.password_hash) is True
    assert verify_password("OldPassword123!", user.password_hash) is False


def test_change_password_wrong_current_password(client: TestClient, db_session: Session, auth_header_and_user):
    """
    [SCRUM-72 / S1-04] Test đổi mật khẩu khi nhập sai mật khẩu hiện tại -> Phải bị từ chối 400.
    """
    headers, user = auth_header_and_user

    response = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "WrongPassword999!",
            "new_password": "BrandNewSecurePassword2026!",
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert "Mật khẩu hiện tại không chính xác" in response.json()["detail"]


def test_change_password_weak_new_password(client: TestClient, db_session: Session, auth_header_and_user):
    """
    [SCRUM-72 / S1-04] Test validate mật khẩu mới: quá ngắn (<8 ký tự) hoặc thiếu chữ/số -> Phải bị từ chối 400.
    """
    headers, user = auth_header_and_user

    # 1. Quá ngắn (< 8 ký tự)
    resp_short = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "OldPassword123!",
            "new_password": "Pass1",
        },
        headers=headers,
    )
    assert resp_short.status_code == 400
    assert "8 ký tự" in resp_short.json()["detail"]

    # 2. Không có chữ số
    resp_no_digit = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "OldPassword123!",
            "new_password": "OnlyLettersNoDigits",
        },
        headers=headers,
    )
    assert resp_no_digit.status_code == 400
    assert "chữ cái và chữ số" in resp_no_digit.json()["detail"]


def test_change_password_unauthorized(client: TestClient):
    """
    [SCRUM-72 / S1-04] Test gọi endpoint đổi mật khẩu khi chưa đăng nhập -> 401 Unauthorized.
    """
    response = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "OldPassword123!",
            "new_password": "BrandNewPassword123!",
        },
    )
    assert response.status_code == 401
