"""
Bộ kiểm thử mở rộng cho Phân hệ Nhập Người Dùng Hàng Loạt (Bulk User Import & Background Job):
- Kiểm thử tải CSV template và kiểm tra header BOM UTF-8
- Kiểm thử Preview tệp CSV (.csv) với phân loại NEW, EXISTING, DUPLICATE_FILE, INVALID
- Kiểm thử tạo Background Import Job (/users/import/jobs)
- Kiểm thử truy vấn tiến độ công việc (/users/import/jobs/{id})
- Kiểm thử tải báo cáo lỗi dạng CSV (/users/import/jobs/{id}/errors.csv)
- Kiểm thử danh sách công việc (/users/import/jobs)
- Kiểm thử phân quyền RBAC (chặn nhân viên thường)
"""
import io
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_import_job import UserImportJob
from app.core.security import hash_password, create_access_token


@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = User(
        id="usr-bulk-admin",
        email="bulk_admin@nexuscrm.vn",
        password_hash=hash_password("AdminPass123!"),
        full_name="Quản Trị Viên Bulk Import",
        role="Super Admin",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def staff_user(db_session: Session) -> User:
    user = User(
        id="usr-bulk-staff",
        email="bulk_staff@nexuscrm.vn",
        password_hash=hash_password("StaffPass123!"),
        full_name="Nhân Viên Sales Bulk",
        role="sales",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    token = create_access_token(admin_user.id, admin_user.email, admin_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def staff_headers(staff_user: User) -> dict:
    token = create_access_token(staff_user.id, staff_user.email, staff_user.role)
    return {"Authorization": f"Bearer {token}"}


def test_download_csv_template(client: TestClient, admin_headers: dict):
    response = client.get("/api/v1/users/import/template?format=csv", headers=admin_headers)
    assert response.status_code == 200
    assert "users_import_template.csv" in response.headers.get("content-disposition", "")
    assert "text/csv" in response.headers.get("content-type", "")

    content = response.content.decode("utf-8-sig")
    assert "full_name,email,phone,role,department" in content
    assert "nguyenvana@nexuscrm.vn" in content


def test_preview_csv_file(client: TestClient, admin_headers: dict, admin_user: User):
    csv_data = (
        "full_name,email,phone,role,department\n"
        "Nguyễn Hợp Lệ,hop_le_csv@nexuscrm.vn,0912345678,Account Executive,Kinh Doanh Miền Bắc\n"
        f"Trùng Admin,{admin_user.email},0912345678,Account Executive,Kinh Doanh\n"
        "Trùng Trong File,hop_le_csv@nexuscrm.vn,0912345678,Account Executive,Kinh Doanh\n"
        ",khong_co_ten@nexuscrm.vn,0912345678,sales,Kinh Doanh\n"
    )

    files = {"file": ("users.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    response = client.post("/api/v1/users/import/preview", files=files, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_rows"] == 4
    assert data["valid_count"] == 1
    assert data["error_count"] == 3

    details = data["details"]
    assert details[0]["status"] == "VALID"
    assert details[0]["classification"] == "NEW"

    assert details[1]["status"] == "INVALID"
    assert details[1]["classification"] == "EXISTING"

    assert details[2]["status"] == "INVALID"
    assert details[2]["classification"] == "DUPLICATE_FILE"

    assert details[3]["status"] == "INVALID"
    assert details[3]["classification"] == "INVALID"


def test_create_and_poll_background_job(client: TestClient, admin_headers: dict, db_session: Session):
    csv_data = (
        "full_name,email,phone,role,department\n"
        "User Job 1,job_user1@nexuscrm.vn,0911223344,Account Executive,Kinh Doanh\n"
        "User Job 2,job_user2@nexuscrm.vn,0922334455,Sales Manager,Kinh Doanh\n"
        "Lỗi Thiếu Tên,,0933445566,sales,Kinh Doanh\n"
    )

    files = {"file": ("batch_test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    response = client.post("/api/v1/users/import/jobs?batch_size=500", files=files, headers=admin_headers)
    assert response.status_code == 202
    job_data = response.json()

    assert "id" in job_data
    assert job_data["total_rows"] == 3
    job_id = job_data["id"]

    # Poll status
    time.sleep(0.5)
    poll_res = client.get(f"/api/v1/users/import/jobs/{job_id}", headers=admin_headers)
    assert poll_res.status_code == 200
    status_data = poll_res.json()
    assert status_data["id"] == job_id
    assert status_data["status"] in ("pending", "processing", "completed")

    # List jobs
    list_res = client.get("/api/v1/users/import/jobs", headers=admin_headers)
    assert list_res.status_code == 200
    jobs_list = list_res.json()
    assert any(j["id"] == job_id for j in jobs_list)

    # Download error report CSV
    err_res = client.get(f"/api/v1/users/import/jobs/{job_id}/errors.csv", headers=admin_headers)
    assert err_res.status_code == 200
    assert "text/csv" in err_res.headers.get("content-type", "")


def test_staff_cannot_create_or_view_jobs(client: TestClient, staff_headers: dict):
    response = client.post("/api/v1/users/import/jobs", headers=staff_headers, json={"rows": []})
    assert response.status_code == 403

    response = client.get("/api/v1/users/import/jobs", headers=staff_headers)
    assert response.status_code == 403
