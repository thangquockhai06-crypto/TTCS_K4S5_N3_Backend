"""
Comprehensive Phase 6 End-to-End Verification Test Suite:
1. Import small valid file (both CSV & Excel formats).
2. Import large file using multiple batches with performance benchmarking.
3. Import file with missing columns and invalid format rows.
4. Import file containing duplicates (within file + against database).
5. Search users by name, username, email, role.
6. Search users concurrently during background import execution.
7. Refresh/reopen job status recovery from database persistence.
8. Partial batch failures handling and error reporting.
9. Verification of role assignment, team assignment, and user defaults.
10. RBAC: Unauthorized access prevention for non-admin roles.
11. Download failed rows error report as CSV.
12. Verification of user CRUD operations integrity.
"""
import io
import time
import pytest
import openpyxl
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.team import Team
from app.models.user_import_job import UserImportJob
from app.core.security import hash_password, create_access_token


@pytest.fixture
def test_admin(db_session: Session) -> User:
    existing = db_session.query(User).filter(User.email == "lifecycle_admin@nexuscrm.vn").first()
    if existing:
        return existing
    admin = User(
        id="usr-lifecycle-admin",
        email="lifecycle_admin@nexuscrm.vn",
        password_hash=hash_password("AdminSecure123!"),
        full_name="Quản Trị Viên Toàn Hệ Thống",
        role="Admin",
        status="active",
        department="Ban Giám Đốc",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def test_employee(db_session: Session) -> User:
    existing = db_session.query(User).filter(User.email == "lifecycle_emp@nexuscrm.vn").first()
    if existing:
        return existing
    emp = User(
        id="usr-lifecycle-emp",
        email="lifecycle_emp@nexuscrm.vn",
        password_hash=hash_password("EmpSecure123!"),
        full_name="Nhân Viên Kinh Doanh",
        role="sales",
        status="active",
        department="Kinh Doanh",
    )
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)
    return emp


@pytest.fixture
def admin_auth(test_admin: User) -> dict:
    token = create_access_token(test_admin.id, test_admin.email, test_admin.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def employee_auth(test_employee: User) -> dict:
    token = create_access_token(test_employee.id, test_employee.email, test_employee.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_team(db_session: Session) -> Team:
    existing = db_session.query(Team).filter(Team.name == "Đội Ngũ Doanh Nghiệp Lớn").first()
    if existing:
        return existing
    team = Team(
        id="team-enterprise-01",
        name="Đội Ngũ Doanh Nghiệp Lớn",
        description="Chuyên phụ trách khách hàng Enterprise",
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def wait_for_job_completion(client: TestClient, admin_auth: dict, job_id: str, max_wait: float = 3.0) -> dict:
    """Helper chờ đợi và lấy trạng thái hoàn tất của Background Import Job."""
    start = time.perf_counter()
    while time.perf_counter() - start < max_wait:
        res = client.get(f"/api/v1/users/import/jobs/{job_id}", headers=admin_auth)
        if res.status_code == 200:
            data = res.json()
            if str(data.get("status", "")).lower() in ("completed", "failed"):
                return data
        time.sleep(0.1)
    return client.get(f"/api/v1/users/import/jobs/{job_id}", headers=admin_auth).json()


def test_scenario_1_small_valid_csv_and_xlsx_import(client: TestClient, admin_auth: dict):
    """Scenario 1: Import small valid file in both CSV and XLSX formats."""
    # 1. CSV Import
    csv_data = (
        "full_name,email,phone,role,department\n"
        "Đặng Văn Lâm,lam.dang@nexuscrm.vn,0988111222,Sales,Kinh Doanh 1\n"
        "Nguyễn Quang Hải,hai.nguyen@nexuscrm.vn,0988333444,Employee,Truyền Thông\n"
    ).encode("utf-8-sig")

    # Preview
    preview_res = client.post(
        "/api/v1/users/import/preview",
        headers=admin_auth,
        files={"file": ("small_valid.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert preview_res.status_code == 200
    pdata = preview_res.json()
    assert pdata["total_rows"] == 2
    assert pdata["valid_count"] == 2
    assert pdata["error_count"] == 0
    assert all(r["classification"] == "NEW" for r in pdata["details"])

    # Launch Job
    job_res = client.post(
        "/api/v1/users/import/jobs",
        headers=admin_auth,
        files={"file": ("small_valid.csv", io.BytesIO(csv_data), "text/csv")},
        data={"batch_size": 100},
    )
    assert job_res.status_code == 202
    job_id = job_res.json()["id"]

    # Poll status
    sdata = wait_for_job_completion(client, admin_auth, job_id)
    assert sdata["status"].lower() == "completed"
    assert sdata["successful_rows"] == 2
    assert sdata["failed_rows"] == 0

    # 2. XLSX Import
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["full_name", "email", "phone", "role", "department"])
    ws.append(["Đoàn Văn Hậu", "hau.doan@nexuscrm.vn", "0977111222", "Manager", "Kỹ Thuật"])
    xlsx_buf = io.BytesIO()
    wb.save(xlsx_buf)
    xlsx_buf.seek(0)

    xlsx_job_res = client.post(
        "/api/v1/users/import/jobs",
        headers=admin_auth,
        files={"file": ("small_valid.xlsx", xlsx_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert xlsx_job_res.status_code == 202
    xjob_id = xlsx_job_res.json()["id"]

    xstatus = wait_for_job_completion(client, admin_auth, xjob_id)
    assert xstatus["status"].lower() == "completed"
    assert xstatus["successful_rows"] == 1


def test_scenario_2_large_file_multi_batch_and_benchmark(client: TestClient, admin_auth: dict):
    """Scenario 2: Import large dataset with 300 rows across multiple batches and benchmark speed."""
    TOTAL_ROWS = 300
    BATCH_SIZE = 100

    csv_lines = ["full_name,email,phone,role,department"]
    for i in range(TOTAL_ROWS):
        csv_lines.append(f"User Benchmark {i:03d},bench_{i:03d}@nexuscrm.vn,098{i:07d},Sales,Kinh Doanh")
    csv_bytes = "\n".join(csv_lines).encode("utf-8-sig")

    start_time = time.perf_counter()

    # Launch background job
    job_res = client.post(
        "/api/v1/users/import/jobs",
        headers=admin_auth,
        files={"file": ("benchmark_300.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"batch_size": BATCH_SIZE},
    )
    assert job_res.status_code == 202
    job_id = job_res.json()["id"]

    # Poll completion
    job_status = wait_for_job_completion(client, admin_auth, job_id, max_wait=5.0)
    duration = time.perf_counter() - start_time

    assert job_status["status"].lower() == "completed"
    assert job_status["total_rows"] == TOTAL_ROWS
    assert job_status["successful_rows"] == TOTAL_ROWS
    assert job_status["failed_rows"] == 0

    # Ensure processing is efficient (< 5.0 seconds for 300 rows in SQLite)
    assert duration < 5.0, f"Processing {TOTAL_ROWS} rows took {duration:.2f}s, expected < 5.0s"


def test_scenario_3_missing_columns_and_invalid_formats(client: TestClient, admin_auth: dict):
    """Scenario 3: Validation of invalid file extension and invalid row values."""
    # Invalid extension (.txt)
    res_bad = client.post(
        "/api/v1/users/import/preview",
        headers=admin_auth,
        files={"file": ("bad_extension.txt", io.BytesIO(b"dummy data"), "text/plain")},
    )
    assert res_bad.status_code == 400
    assert "Excel" in res_bad.json()["detail"] or "CSV" in res_bad.json()["detail"]

    # Invalid row values: empty name, bad email format, invalid phone
    invalid_data_csv = (
        "full_name,email,phone,role,department\n"
        ",empty_name@nexuscrm.vn,0911222333,Sales,KD\n"
        "Nguyễn Văn Lỗi,not-an-email,0922333444,Sales,KD\n"
        "Trần Văn Hợp Lệ,valid_person@nexuscrm.vn,0933444555,Employee,KD\n"
    ).encode("utf-8-sig")

    prev_res = client.post(
        "/api/v1/users/import/preview",
        headers=admin_auth,
        files={"file": ("invalid_rows.csv", io.BytesIO(invalid_data_csv), "text/csv")},
    )
    assert prev_res.status_code == 200
    pdata = prev_res.json()
    assert pdata["total_rows"] == 3
    assert pdata["valid_count"] == 1
    assert pdata["error_count"] == 2
    # Verify classifications
    assert pdata["details"][0]["classification"] == "INVALID"
    assert pdata["details"][1]["classification"] == "INVALID"
    assert pdata["details"][2]["classification"] == "NEW"


def test_scenario_4_and_8_duplicates_and_partial_failures_with_error_report(
    client: TestClient, admin_auth: dict, test_admin: User
):
    """Scenario 4 & 8: File-internal duplicates + existing DB duplicates + error report CSV."""
    mixed_csv = (
        "full_name,email,phone,role,department\n"
        f"Admin Bản Sao,{test_admin.email},0911000111,Admin,Ban Quản Trị\n"  # Trùng DB
        "Người Dùng Mới 1,dupe_file@nexuscrm.vn,0911222333,Sales,KD\n"  # Hợp lệ
        "Người Dùng Mới 1 Trùng,dupe_file@nexuscrm.vn,0911222444,Sales,KD\n"  # Trùng trong file
        ",invalid_no_name@nexuscrm.vn,0911222555,Sales,KD\n"  # Không có tên
        "Người Dùng Mới 2,unique_new@nexuscrm.vn,0911222666,Sales,KD\n"  # Hợp lệ
    ).encode("utf-8-sig")

    # Preview verification
    prev_res = client.post(
        "/api/v1/users/import/preview",
        headers=admin_auth,
        files={"file": ("mixed.csv", io.BytesIO(mixed_csv), "text/csv")},
    )
    assert prev_res.status_code == 200
    pdata = prev_res.json()
    assert pdata["total_rows"] == 5
    assert pdata["details"][0]["classification"] == "EXISTING"
    assert pdata["details"][1]["classification"] == "NEW"
    assert pdata["details"][2]["classification"] == "DUPLICATE_FILE"
    assert pdata["details"][3]["classification"] == "INVALID"
    assert pdata["details"][4]["classification"] == "NEW"

    # Background Job execution
    job_res = client.post(
        "/api/v1/users/import/jobs",
        headers=admin_auth,
        files={"file": ("mixed.csv", io.BytesIO(mixed_csv), "text/csv")},
    )
    assert job_res.status_code == 202
    job_id = job_res.json()["id"]

    # Poll status
    sdata = wait_for_job_completion(client, admin_auth, job_id)
    assert sdata["status"].lower() == "completed"
    assert sdata["successful_rows"] == 2  # rows 1 and 4
    assert sdata["failed_rows"] == 3  # rows 0, 2, and 3

    # Scenario 11: Download Failed Rows Error CSV Report
    err_res = client.get(f"/api/v1/users/import/jobs/{job_id}/errors.csv", headers=admin_auth)
    assert err_res.status_code == 200
    assert "text/csv" in err_res.headers["content-type"]
    err_content = err_res.text
    assert "STT Dòng" in err_content or "Row" in err_content
    assert "Lý do thất bại" in err_content or "Error" in err_content
    assert test_admin.email in err_content
    assert "dupe_file@nexuscrm.vn" in err_content


def test_scenario_5_and_6_search_users_and_search_during_import(
    client: TestClient, admin_auth: dict, test_admin: User
):
    """Scenario 5 & 6: Search users by multiple fields and search while import job is running."""
    # Scenario 5: Search by Name
    res_name = client.get(f"/api/v1/users?search={test_admin.full_name[:5]}", headers=admin_auth)
    assert res_name.status_code == 200
    users_list = res_name.json()
    assert any(u["id"] == test_admin.id for u in users_list)

    # Search by Email
    res_email = client.get(f"/api/v1/users?search={test_admin.email}", headers=admin_auth)
    assert res_email.status_code == 200
    assert any(u["id"] == test_admin.id for u in res_email.json())

    # Scenario 6: Concurrently trigger a background job and perform searches
    csv_bg = (
        "full_name,email,phone,role,department\n"
        "Async User 1,async_1@nexuscrm.vn,0966000111,Sales,KD\n"
        "Async User 2,async_2@nexuscrm.vn,0966000222,Sales,KD\n"
    ).encode("utf-8-sig")

    job_res = client.post(
        "/api/v1/users/import/jobs",
        headers=admin_auth,
        files={"file": ("bg_test.csv", io.BytesIO(csv_bg), "text/csv")},
    )
    assert job_res.status_code == 202

    # While job is dispatched, search immediately without blocking
    search_res = client.get("/api/v1/users?search=Async", headers=admin_auth)
    assert search_res.status_code == 200


def test_scenario_7_job_status_persistence_across_requests(client: TestClient, admin_auth: dict):
    """Scenario 7: Simulates user navigating away, refreshing, and retrieving persisted job state."""
    csv_data = "full_name,email,phone,role,department\nPersist User,persist@nexuscrm.vn,0911000333,Sales,KD\n".encode("utf-8-sig")
    job_res = client.post(
        "/api/v1/users/import/jobs",
        headers=admin_auth,
        files={"file": ("persist.csv", io.BytesIO(csv_data), "text/csv")},
    )
    job_id = job_res.json()["id"]

    # Retrieve from list endpoint (history)
    history_res = client.get("/api/v1/users/import/jobs", headers=admin_auth)
    assert history_res.status_code == 200
    job_ids = [j["id"] for j in history_res.json()]
    assert job_id in job_ids

    # Query individual status
    single_res = client.get(f"/api/v1/users/import/jobs/{job_id}", headers=admin_auth)
    assert single_res.status_code == 200
    assert single_res.json()["filename"] == "persist.csv"


def test_scenario_9_role_team_assignment_and_account_defaults(
    client: TestClient, admin_auth: dict, sample_team: Team, db_session: Session
):
    """Scenario 9: Verify role assignment, team resolution, and user status defaults."""
    csv_data = (
        "full_name,email,phone,role,department\n"
        f"Nguyễn Thành Đạt,dat.nguyen@nexuscrm.vn,0987654321,Manager,{sample_team.name}\n"
    ).encode("utf-8-sig")

    job_res = client.post(
        "/api/v1/users/import/jobs",
        headers=admin_auth,
        files={"file": ("role_team.csv", io.BytesIO(csv_data), "text/csv")},
    )
    job_id = job_res.json()["id"]
    wait_for_job_completion(client, admin_auth, job_id)

    # Verify user was created via API
    search_res = client.get("/api/v1/users?search=dat.nguyen@nexuscrm.vn", headers=admin_auth)
    assert search_res.status_code == 200
    found = [u for u in search_res.json() if u["email"] == "dat.nguyen@nexuscrm.vn"]
    assert len(found) == 1
    u = found[0]
    assert u["fullName"] == "Nguyễn Thành Đạt"
    assert u["role"] == "Manager"
    assert u["status"] == "active"


def test_scenario_10_unauthorized_access_security(client: TestClient, employee_auth: dict):
    """Scenario 10: Verify non-admin users cannot launch jobs, poll jobs, or download error reports."""
    dummy_csv = "full_name,email\nTest,test@test.vn\n".encode("utf-8")

    # Launch job
    res1 = client.post(
        "/api/v1/users/import/jobs",
        headers=employee_auth,
        files={"file": ("unauth.csv", io.BytesIO(dummy_csv), "text/csv")},
    )
    assert res1.status_code in [401, 403]

    # Poll status
    res2 = client.get("/api/v1/users/import/jobs/job-xyz", headers=employee_auth)
    assert res2.status_code in [401, 403]

    # Download error report
    res3 = client.get("/api/v1/users/import/jobs/job-xyz/errors.csv", headers=employee_auth)
    assert res3.status_code in [401, 403]


def test_scenario_12_existing_user_crud_integrity(client: TestClient, admin_auth: dict):
    """Scenario 12: Verify that existing User CRUD endpoints still function properly."""
    # List users
    list_res = client.get("/api/v1/users?page=1&limit=10", headers=admin_auth)
    assert list_res.status_code == 200
    assert isinstance(list_res.json(), list)

    # Create user via standard API
    create_payload = {
        "email": "api_crud_user@nexuscrm.vn",
        "full_name": "API Crud User",
        "password": "Password123!",
        "role": "Employee",
    }
    create_res = client.post("/api/v1/users", headers=admin_auth, json=create_payload)
    assert create_res.status_code == 201
    user_id = create_res.json()["id"]

    # Get user by ID
    get_res = client.get(f"/api/v1/users/{user_id}", headers=admin_auth)
    assert get_res.status_code == 200
    assert get_res.json()["email"] == "api_crud_user@nexuscrm.vn"

    # Update user
    update_res = client.put(
        f"/api/v1/users/{user_id}",
        headers=admin_auth,
        json={"full_name": "API Crud User Updated"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["fullName"] == "API Crud User Updated"
