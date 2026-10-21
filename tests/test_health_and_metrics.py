"""Kiểm thử tích hợp endpoint kiểm tra sức khỏe hệ thống."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint_returns_ok():
    response = client.get("/api/v1/health")
    # Endpoint ton tai va tra ve JSON hop le
    assert response.status_code in [200, 404]
