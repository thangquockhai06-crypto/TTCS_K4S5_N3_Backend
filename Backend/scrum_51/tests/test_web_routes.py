"""
Integration Test - Kiểm thử toàn bộ Web Routes & APIs (Flask) cho SCRUM-51
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import db
from config import STATUS_IN_CARE, STATUS_PENDING_ALLOCATION, STATUS_CONTACTED


class TestWebRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config["TESTING"] = True
        db.reset_demo_data()

    def test_dashboard_route(self):
        """Kiểm tra trang Dashboard hoạt động bình thường"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("SCRUM-51".encode("utf-8"), response.data)
        self.assertIn("Bảng Điều Khiển Tổng Quan".encode("utf-8"), response.data)

    def test_my_leads_route(self):
        """Kiểm tra trang bàn làm việc Sales Rep"""
        response = self.client.get("/my-leads")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Bàn Làm Việc".encode("utf-8"), response.data)
        self.assertIn("Chờ Bạn Tiếp Nhận".encode("utf-8"), response.data)

    def test_team_lead_route(self):
        """Kiểm tra trang Trưởng nhóm"""
        response = self.client.get("/team-lead")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Bàn Điều Phối & Giám Sát".encode("utf-8"), response.data)
        self.assertIn("Hàng Chờ Phân Bổ".encode("utf-8"), response.data)

    def test_accept_lead_via_post(self):
        """Kiểm tra route POST /leads/<id>/accept"""
        lead = db.create_lead("Khách Web Accept", "Cty Web 1", "0911111111", "w1@test.vn", assigned_to_id="usr-01")
        response = self.client.post(f"/leads/{lead['id']}/accept", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        db_lead = db.get_lead(lead["id"])
        self.assertEqual(db_lead["status"], STATUS_IN_CARE)

    def test_reject_lead_empty_reason_fails(self):
        """Kiểm tra submit từ chối bỏ trống lý do bị chặn"""
        lead = db.create_lead("Khách Web Reject Empty", "Cty Web 2", "0922222222", "w2@test.vn", assigned_to_id="usr-01")
        response = self.client.post(
            f"/leads/{lead['id']}/reject",
            data={"reason": ""},
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("BẮT BUỘC NHẬP LÝ DO".encode("utf-8"), response.data)

        # Trạng thái không đổi
        db_lead = db.get_lead(lead["id"])
        self.assertNotEqual(db_lead["status"], STATUS_PENDING_ALLOCATION)

    def test_reject_lead_valid_reason_succeeds(self):
        """Kiểm tra submit từ chối có lý do chuyển sang Hàng chờ phân bổ"""
        lead = db.create_lead("Khách Web Reject Valid", "Cty Web 3", "0933333333", "w3@test.vn", assigned_to_id="usr-01")
        response = self.client.post(
            f"/leads/{lead['id']}/reject",
            data={"reason": "Khách hàng sai ngành nghề phụ trách"},
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Hàng chờ phân bổ".encode("utf-8"), response.data)

        db_lead = db.get_lead(lead["id"])
        self.assertEqual(db_lead["status"], STATUS_PENDING_ALLOCATION)
        self.assertEqual(db_lead["rejection_reason"], "Khách hàng sai ngành nghề phụ trách")

    def test_api_countdown_endpoint(self):
        """Kiểm tra API trả về đếm ngược SLA JSON"""
        lead = db.create_lead("Khách API", "Cty API", "0944444444", "api@test.vn", assigned_to_id="usr-01", sla_seconds=60)
        response = self.client.get(f"/api/leads/{lead['id']}/sla-countdown")
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data["lead_id"], lead["id"])
        self.assertIn("remaining_seconds", json_data)


if __name__ == "__main__":
    unittest.main()
