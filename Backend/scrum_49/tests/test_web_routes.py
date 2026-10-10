"""
Kiểm thử tích hợp các tuyến đường web (Flask Integration Tests)
Đảm bảo tất cả trang và API hoạt động trơn tru
"""

import unittest
from app import app
from database import db

class TestFlaskWebRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_dashboard_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("AutoLead CRM".encode("utf-8"), response.data)
        self.assertIn("SCRUM-49".encode("utf-8"), response.data)

    def test_rules_page_and_add_rule(self):
        # 1. Truy cập trang rules
        response = self.client.get("/rules")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Quy Tắc Phân Bổ Lead Tự Động".encode("utf-8"), response.data)

        # 2. Thêm quy tắc mới
        add_res = self.client.post("/rules/add", data={
            "name": "Quy tắc Kiểm Thử Miền Nam",
            "priority": 1,
            "region": "Miền Nam",
            "industry": "Bất động sản",
            "assignment_type": "ROUND_ROBIN",
            "target_team_id": "team-nam",
            "description": "Rule tạo từ integration test"
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)
        self.assertIn("Quy tắc Kiểm Thử Miền Nam".encode("utf-8"), add_res.data)

    def test_leads_page_and_add_lead(self):
        # 1. Truy cập trang leads
        response = self.client.get("/leads")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Danh Sách Lead".encode("utf-8"), response.data)

        # 2. Thêm lead mới
        add_res = self.client.post("/leads/add", data={
            "name": "Tập Đoàn Hoa Sen Test",
            "contact_person": "Nguyễn Văn Test",
            "phone": "0911223344",
            "region": "Miền Bắc",
            "industry": "Tài chính - Ngân hàng",
            "estimated_value": "120000000",
            "source": "Website Form"
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)
        self.assertIn("Tập Đoàn Hoa Sen Test".encode("utf-8"), add_res.data)

    def test_manual_queue_and_assign(self):
        # 1. Truy cập trang hàng chờ phân tay
        response = self.client.get("/manual-queue")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Hàng Chờ Phân Tay Dành Cho Trưởng Nhóm".encode("utf-8"), response.data)

    def test_team_reps_page(self):
        response = self.client.get("/team-reps")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Round-Robin".encode("utf-8"), response.data)

    def test_worker_monitor_page(self):
        response = self.client.get("/worker-monitor")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Luồng Chạy Nền".encode("utf-8"), response.data)

    def test_api_status_endpoint(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("metrics", data)
        self.assertIn("worker", data)

if __name__ == "__main__":
    unittest.main()
