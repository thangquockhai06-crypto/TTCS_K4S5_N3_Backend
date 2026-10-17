"""Kiểm thử cơ chế bảo mật xác thực khi token không hợp lệ."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_invalid_token_returns_401():
    headers = {"Authorization": "Bearer invalid_secret_token_xyz"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401
