"""
Bộ kiểm thử tự động toàn diện cho tính năng:
'Nhắc việc sắp đến hạn và việc quá hạn cho Nhân viên kinh doanh'
Bao phủ:
1. Quản lý công việc (CRUD Task & Centralized Data Scope)
2. Cấu hình mốc nhắc nhở (Reminder Settings GET/PUT)
3. Tiến trình quét chạy ngầm (Idempotent Reminder & Overdue Scanner)
4. Dashboard cá nhân cho Nhân viên kinh doanh
5. Báo cáo thống kê cho Trưởng nhóm (RBAC 403 / 200)
6. Thông báo trong ứng dụng (In-app Notifications)
"""
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.reminder_setting import ReminderSetting
from app.models.notification import Notification
from app.services.task_reminder_service import TaskReminderService


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 1. CẤU HÌNH MỐC NHẮC VIỆC (REMINDER SETTINGS)
# =============================================================================

def test_get_default_reminder_settings(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["emp_a"]
    response = client.get("/api/v1/tasks/reminder-settings", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert "remindBeforeMinutes" in data
    # Mặc định có mốc 15, 60, 1440
    assert 15 in data["remindBeforeMinutes"]
    assert 60 in data["remindBeforeMinutes"]
    assert 1440 in data["remindBeforeMinutes"]
    assert data["notifyOnOverdue"] is True
    assert data["enableInApp"] is True


def test_update_reminder_settings_success(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["emp_a"]
    payload = {
        "remindBeforeMinutes": [30, 120, 2880],  # 30p, 2h, 2 ngày
        "notifyOnOverdue": True,
        "enableInApp": True,
        "enableEmail": True,
    }
    response = client.put("/api/v1/tasks/reminder-settings", json=payload, headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert data["remindBeforeMinutes"] == [30, 120, 2880]
    assert data["enableEmail"] is True

    # Kiểm tra lại bằng GET
    get_res = client.get("/api/v1/tasks/reminder-settings", headers=auth_header(token))
    assert get_res.json()["remindBeforeMinutes"] == [30, 120, 2880]


def test_update_reminder_settings_invalid(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["emp_a"]
    payload = {
        "remindBeforeMinutes": [-10, 0],
    }
    response = client.put("/api/v1/tasks/reminder-settings", json=payload, headers=auth_header(token))
    assert response.status_code == 400
    assert "phải chứa ít nhất một mốc phút lớn hơn 0" in response.json()["detail"]


# =============================================================================
# 2. CRUD CÔNG VIỆC & CENTRALIZED DATA SCOPE
# =============================================================================

def test_create_and_get_task(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["emp_a"]
    due = (datetime.utcnow() + timedelta(days=1)).isoformat()
    payload = {
        "title": "Soạn thảo hợp đồng giải pháp CRM",
        "description": "Chuẩn bị bản in và gửi chuyển phát nhanh",
        "dueDate": due,
        "priority": "high",
    }
    res = client.post("/api/v1/tasks", json=payload, headers=auth_header(token))
    assert res.status_code == 201
    task_data = res.json()
    assert task_data["title"] == "Soạn thảo hợp đồng giải pháp CRM"
    assert task_data["assigneeId"] == seed_data["users"]["emp_a"].id
    assert task_data["status"] == "pending"
    assert task_data["isOverdue"] is False

    task_id = task_data["id"]

    # Xem chi tiết
    detail_res = client.get(f"/api/v1/tasks/{task_id}", headers=auth_header(token))
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == task_id


def test_task_data_scope_isolation(client: TestClient, seed_data: dict, db_session: Session):
    token_emp_a = seed_data["tokens"]["emp_a"]
    token_emp_b = seed_data["tokens"]["emp_b"]
    token_leader = seed_data["tokens"]["team_leader"]
    token_director = seed_data["tokens"]["sales_director"]

    # Tạo 1 task của Emp A
    task_a = Task(
        title="Công việc riêng của A",
        due_date=datetime.utcnow() + timedelta(hours=5),
        assignee_id=seed_data["users"]["emp_a"].id,
        creator_id=seed_data["users"]["emp_a"].id,
        status="pending",
    )
    # Tạo 1 task của Emp Beta (khác team)
    task_beta = Task(
        title="Công việc của Beta khác team",
        due_date=datetime.utcnow() + timedelta(hours=5),
        assignee_id=seed_data["users"]["emp_beta"].id,
        creator_id=seed_data["users"]["emp_beta"].id,
        status="pending",
    )
    db_session.add_all([task_a, task_beta])
    db_session.commit()

    # 1. Emp A chỉ thấy task của mình (OWN)
    res_a = client.get("/api/v1/tasks", headers=auth_header(token_emp_a))
    assert res_a.status_code == 200
    titles_a = [t["title"] for t in res_a.json()]
    assert "Công việc riêng của A" in titles_a
    assert "Công việc của Beta khác team" not in titles_a

    # 2. Emp B không thấy task của A (cùng team nhưng scope OWN)
    res_b = client.get("/api/v1/tasks", headers=auth_header(token_emp_b))
    assert res_b.status_code == 200
    titles_b = [t["title"] for t in res_b.json()]
    assert "Công việc riêng của A" not in titles_b

    # 3. Emp B cố truy cập trực tiếp ID task của A -> 403 Forbidden
    res_b_direct = client.get(f"/api/v1/tasks/{task_a.id}", headers=auth_header(token_emp_b))
    assert res_b_direct.status_code == 403

    # 4. Team Leader (Team Alpha) thấy task của A nhưng KHÔNG thấy task của Beta
    res_lead = client.get("/api/v1/tasks", headers=auth_header(token_leader))
    assert res_lead.status_code == 200
    titles_lead = [t["title"] for t in res_lead.json()]
    assert "Công việc riêng của A" in titles_lead
    assert "Công việc của Beta khác team" not in titles_lead

    # 5. Sales Director (Phạm vi ALL) thấy tất cả các task
    res_dir = client.get("/api/v1/tasks", headers=auth_header(token_director))
    assert res_dir.status_code == 200
    titles_dir = [t["title"] for t in res_dir.json()]
    assert "Công việc riêng của A" in titles_dir
    assert "Công việc của Beta khác team" in titles_dir


# =============================================================================
# 3. TIẾN TRÌNH QUÉT NHẮC VIỆC & QUÁ HẠN (BACKGROUND JOB / SCANNER)
# =============================================================================

def test_reminder_and_overdue_scan_idempotence(client: TestClient, seed_data: dict, db_session: Session):
    emp_a_id = seed_data["users"]["emp_a"].id
    now = datetime.utcnow()

    # Tạo 1 task quá hạn
    overdue_task = Task(
        title="Bảo trì máy chủ CRM quá hạn",
        due_date=now - timedelta(hours=3),
        assignee_id=emp_a_id,
        status="pending",
        reminded_milestones=[],
    )
    # Tạo 1 task sắp đến hạn (trong 40 phút, nhỏ hơn mốc 60m)
    due_soon_task = Task(
        title="Gặp gỡ khách hàng FPT Telecom",
        due_date=now + timedelta(minutes=40),
        assignee_id=emp_a_id,
        status="pending",
        reminded_milestones=[],
    )
    # Tạo 1 task xa trong tương lai (5 ngày nữa)
    future_task = Task(
        title="Họp tổng kết quý sau 5 ngày",
        due_date=now + timedelta(days=5),
        assignee_id=emp_a_id,
        status="pending",
        reminded_milestones=[],
    )
    db_session.add_all([overdue_task, due_soon_task, future_task])
    db_session.commit()

    # Kích hoạt quét lần 1 qua API trigger-scan
    token_director = seed_data["tokens"]["sales_director"]
    scan_res = client.post("/api/v1/tasks/trigger-scan", headers=auth_header(token_director))
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    assert scan_data["overdueMarked"] >= 1
    assert scan_data["remindersSent"] >= 1

    db_session.refresh(overdue_task)
    db_session.refresh(due_soon_task)
    db_session.refresh(future_task)

    # 1. Task quá hạn: status đổi thành overdue, có mốc 'overdue'
    assert overdue_task.status == "overdue"
    assert "overdue" in (overdue_task.reminded_milestones or [])

    # 2. Task sắp đến hạn: đã được gắn mốc '60m' (hoặc 1440m)
    assert any(m in (due_soon_task.reminded_milestones or []) for m in ["60m", "1440m"])

    # 3. Task tương lai xa: không bị đánh dấu nhắc sớm
    assert "15m" not in (future_task.reminded_milestones or [])
    assert "60m" not in (future_task.reminded_milestones or [])

    # 4. Kiểm tra thông báo sinh ra trong DB
    notifs = db_session.query(Notification).filter(Notification.user_id == emp_a_id).all()
    assert len(notifs) >= 2
    notif_types = [n.type for n in notifs]
    assert "task_overdue" in notif_types
    assert "task_reminder" in notif_types

    # 5. IDEMPOTENT TEST: Kích hoạt quét lần 2
    notif_count_before = len(notifs)
    scan_res_2 = client.post("/api/v1/tasks/trigger-scan", headers=auth_header(token_director))
    assert scan_res_2.status_code == 200
    # Không gửi trùng lặp thêm thông báo nào cho các mốc đã quét
    notifs_after = db_session.query(Notification).filter(Notification.user_id == emp_a_id).all()
    assert len(notifs_after) == notif_count_before


# =============================================================================
# 4. TRANG CHỦ CÁ NHÂN (PERSONAL DASHBOARD CHO NHÂN VIÊN KINH DOANH)
# =============================================================================

def test_personal_dashboard(client: TestClient, seed_data: dict, db_session: Session):
    emp_a = seed_data["users"]["emp_a"]
    token = seed_data["tokens"]["emp_a"]
    now = datetime.utcnow()

    # Dọn dẹp task cũ của emp_a và tạo mới dữ liệu chuẩn
    db_session.query(Task).filter(Task.assignee_id == emp_a.id).delete()
    db_session.commit()

    task_overdue = Task(
        title="Task quá hạn hôm qua",
        due_date=now - timedelta(days=1),
        assignee_id=emp_a.id,
        status="overdue",
    )
    task_due_soon = Task(
        title="Task sắp đến hạn chiều nay",
        due_date=now + timedelta(hours=2),
        assignee_id=emp_a.id,
        status="in_progress",
    )
    task_done = Task(
        title="Task đã hoàn thành xuất sắc",
        due_date=now - timedelta(hours=10),
        assignee_id=emp_a.id,
        status="completed",
        completed_at=now - timedelta(hours=1),
    )
    db_session.add_all([task_overdue, task_due_soon, task_done])
    db_session.commit()

    res = client.get("/api/v1/tasks/my-dashboard", headers=auth_header(token))
    assert res.status_code == 200
    data = res.json()

    # Kiểm tra stats
    stats = data["stats"]
    assert stats["totalTasks"] == 3
    assert stats["completedTasks"] == 1
    assert stats["overdueTasksCount"] == 1
    assert stats["dueSoonTasksCount"] == 1
    assert "33." in stats["completionRate"]

    # Kiểm tra danh sách overdueTasks
    overdue_list = data["overdueTasks"]
    assert len(overdue_list) == 1
    assert overdue_list[0]["title"] == "Task quá hạn hôm qua"
    assert overdue_list[0]["isOverdue"] is True
    assert "Quá hạn" in overdue_list[0]["overdueDisplay"]

    # Kiểm tra danh sách dueSoonTasks
    due_soon_list = data["dueSoonTasks"]
    assert len(due_soon_list) == 1
    assert due_soon_list[0]["title"] == "Task sắp đến hạn chiều nay"
    assert due_soon_list[0]["isDueSoon"] is True
    assert "Còn" in due_soon_list[0]["timeRemainingDisplay"]


# =============================================================================
# 5. THỐNG KÊ CHO TRƯỞNG NHÓM (TEAM LEAD / MANAGER)
# =============================================================================

def test_team_lead_statistics_permissions(client: TestClient, seed_data: dict):
    token_emp_a = seed_data["tokens"]["emp_a"]
    token_leader = seed_data["tokens"]["team_leader"]
    token_director = seed_data["tokens"]["sales_director"]

    # 1. Nhân viên kinh doanh thông thường (DataScope.OWN) -> 403 Forbidden
    res_emp = client.get("/api/v1/tasks/team-lead/statistics", headers=auth_header(token_emp_a))
    assert res_emp.status_code == 403
    assert "không có quyền" in res_emp.json()["detail"]

    # 2. Trưởng nhóm (DataScope.TEAM) -> 200 OK
    res_lead = client.get("/api/v1/tasks/team-lead/statistics", headers=auth_header(token_leader))
    assert res_lead.status_code == 200
    lead_data = res_lead.json()
    assert "members" in lead_data
    assert "teamTotalTasks" in lead_data
    assert "teamOverdueTasks" in lead_data

    # 3. Giám đốc kinh doanh / Admin (DataScope.ALL) -> 200 OK
    res_dir = client.get("/api/v1/tasks/team-lead/statistics", headers=auth_header(token_director))
    assert res_dir.status_code == 200


def test_team_lead_statistics_data_accuracy(client: TestClient, seed_data: dict, db_session: Session):
    leader = seed_data["users"]["team_leader"]
    token_leader = seed_data["tokens"]["team_leader"]
    emp_a = seed_data["users"]["emp_a"]
    emp_b = seed_data["users"]["emp_b"]
    now = datetime.utcnow()

    # Dọn dẹp tasks của cả 2 nhân viên
    db_session.query(Task).filter(Task.assignee_id.in_([emp_a.id, emp_b.id])).delete()
    db_session.commit()

    # Emp A có 2 task quá hạn, 1 task xong
    t_a1 = Task(title="Task A1 Quá hạn", due_date=now - timedelta(days=2), assignee_id=emp_a.id, status="overdue")
    t_a2 = Task(title="Task A2 Quá hạn", due_date=now - timedelta(hours=5), assignee_id=emp_a.id, status="overdue")
    t_a3 = Task(title="Task A3 Đã xong", due_date=now - timedelta(days=1), assignee_id=emp_a.id, status="completed", completed_at=now)

    # Emp B có 1 task sắp đến hạn, không quá hạn
    t_b1 = Task(title="Task B1 Sắp hạn", due_date=now + timedelta(hours=1), assignee_id=emp_b.id, status="pending")

    db_session.add_all([t_a1, t_a2, t_a3, t_b1])
    db_session.commit()

    res = client.get("/api/v1/tasks/team-lead/statistics", headers=auth_header(token_leader))
    assert res.status_code == 200
    data = res.json()

    # Tổng kết nhóm
    assert data["teamOverdueTasks"] >= 2
    assert data["teamCompletedTasks"] >= 1

    # Chi tiết từng thành viên
    members = data["members"]
    emp_a_stat = next((m for m in members if m["userId"] == emp_a.id), None)
    emp_b_stat = next((m for m in members if m["userId"] == emp_b.id), None)

    assert emp_a_stat is not None
    assert emp_a_stat["totalTasks"] == 3
    assert emp_a_stat["overdueTasksCount"] == 2
    assert emp_a_stat["completedTasks"] == 1
    assert len(emp_a_stat["overdueTasks"]) == 2

    assert emp_b_stat is not None
    assert emp_b_stat["overdueTasksCount"] == 0
    assert emp_b_stat["dueSoonTasksCount"] == 1


# =============================================================================
# 6. IN-APP NOTIFICATIONS API
# =============================================================================

def test_in_app_notifications_lifecycle(client: TestClient, seed_data: dict, db_session: Session):
    emp_a = seed_data["users"]["emp_a"]
    token = seed_data["tokens"]["emp_a"]

    # Tạo 2 thông báo
    notif1 = Notification(
        user_id=emp_a.id,
        title="Thông báo 1",
        message="Nội dung 1",
        is_read=False,
    )
    notif2 = Notification(
        user_id=emp_a.id,
        title="Thông báo 2",
        message="Nội dung 2",
        is_read=False,
    )
    db_session.add_all([notif1, notif2])
    db_session.commit()

    # 1. Đếm số chưa đọc
    count_res = client.get("/api/v1/notifications/unread-count", headers=auth_header(token))
    assert count_res.status_code == 200
    assert count_res.json()["unreadCount"] >= 2

    # 2. Đánh dấu đã đọc thông báo 1
    read_res = client.patch(f"/api/v1/notifications/{notif1.id}/read", headers=auth_header(token))
    assert read_res.status_code == 200
    assert read_res.json()["isRead"] is True

    # 3. Đánh dấu đọc tất cả
    mark_all_res = client.post("/api/v1/notifications/mark-all-read", headers=auth_header(token))
    assert mark_all_res.status_code == 200
    assert mark_all_res.json()["status"] == "success"

    # Kiểm tra lại số chưa đọc
    count_after = client.get("/api/v1/notifications/unread-count", headers=auth_header(token))
    assert count_after.json()["unreadCount"] == 0

