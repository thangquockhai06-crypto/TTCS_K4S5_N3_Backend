"""
Bộ kiểm thử tự động cho SCRUM-71 / S1-03: Đặt lại mật khẩu qua Email (FastAPI Backend).
- POST /api/v1/auth/forgot-password (secrets.token_urlsafe, Redis 30p, Anti-Enumeration)
- POST /api/v1/auth/reset-password (Liên kết dùng 01 lần, đổi mật khẩu)
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
from app.core.security import hash_password, verify_password
from app.core.redis_client import redis_manager



def test_forgot_password_success(client: TestClient, db_session: Session):
    """
    [SCRUM-71 / S1-03] Test gửi yêu cầu đặt lại mật khẩu với email tồn tại trong CSDL.
    """
    user = User(
        id="test-fp-01",
        full_name="Nguyễn Văn Test FP",
        email="test_fp_user@nexuscrm.vn",
        password_hash=hash_password("OldPassword123!"),
        role="staff",
        status="active",
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "test_fp_user@nexuscrm.vn"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "30 phút" in data["message"]


def test_forgot_password_anti_enumeration(client: TestClient, db_session: Session):
    """
    [SCRUM-71 / S1-03] Test Anti-Enumeration: Email không tồn tại vẫn trả về cùng thông báo HTTP 200.
    """
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "non_existent_hacker_email@external.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "30 phút" in data["message"]


def test_reset_password_flow_and_single_use(client: TestClient, db_session: Session):
    """
    [SCRUM-71 / S1-03] Test luồng đổi mật khẩu đầy đủ:
    1. Sinh token qua secrets.token_urlsafe() & lưu Redis
    2. Đổi mật khẩu thành công qua /reset-password
    3. Thử dùng lại token lần 2 -> Thất bại (Liên kết chỉ dùng được 01 lần)
    """
    email = "single_use_test@nexuscrm.vn"
    user = User(
        id="test-fp-02",
        full_name="Single Use User",
        email=email,
        password_hash=hash_password("OldPassword123!"),
        role="staff",
        status="active",
    )
    db_session.add(user)
    db_session.commit()

    # 1. Tự sinh token như AuthService làm
    token = "test_token_urlsafe_abc123xyz"
    redis_manager.set_reset_token(token, email, ttl_seconds=1800)

    # 2. Gọi endpoint reset-password lần đầu -> Thành công
    new_pass = "BrandNewPassword2026!"
    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_pass},
    )
    assert reset_resp.status_code == 200
    assert "thành công" in reset_resp.json()["message"]

    # Kiểm tra mật khẩu trong DB đã thay đổi
    db_session.refresh(user)
    assert verify_password(new_pass, user.password_hash) is True

    # 3. Thử dùng lại token lần 2 -> Phải bị từ chối 400 Bad Request
    reuse_resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "AnotherPassword999!"},
    )
    assert reuse_resp.status_code == 400
    assert "không hợp lệ hoặc đã hết hạn" in reuse_resp.json()["detail"]


def test_reset_password_invalid_token(client: TestClient):
    """
    [SCRUM-71 / S1-03] Test reset password với token giả/hết hạn.
    """
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "invalid_fake_token_999", "new_password": "Password123!"},
    )
    assert response.status_code == 400
    assert "không hợp lệ hoặc đã hết hạn" in response.json()["detail"]
