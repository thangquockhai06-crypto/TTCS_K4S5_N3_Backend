"""
Kiểm thử tích hợp các Web Routes & REST APIs - Ticket SCRUM-54
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import db, STATUS_QUALIFIED, STATUS_CONVERTED


class TestWebRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        db.reset_demo_data()

    def test_dashboard_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("SCRUM-54".encode("utf-8"), response.data)

    def test_leads_list_route(self):
        response = self.client.get("/leads")
        self.assertEqual(response.status_code, 200)
        self.assertIn("LEAD-101".encode("utf-8"), response.data)

    def test_lead_detail_route(self):
        response = self.client.get("/leads/LEAD-101")
        self.assertEqual(response.status_code, 200)
        self.assertIn("VinTech".encode("utf-8"), response.data)

    def test_lead_convert_get_preview(self):
        """Kiểm tra màn hình xem trước 3 thực thể chuyển đổi"""
        response = self.client.get("/leads/LEAD-101/convert")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Xem Trước Chuyển Đổi".encode("utf-8"), response.data)

    def test_lead_convert_post_action(self):
        """Kiểm tra gửi form chuyển đổi thành công"""
        response = self.client.post("/leads/LEAD-101/convert", data={
            "opportunity_name": "Gói CRM Tùy Chỉnh VinTech",
            "opportunity_amount": "160000000",
            "opportunity_stage": "PROPOSAL"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Kiểm tra lead đã chuyển sang trạng thái đã chuyển đổi
        lead = db.get_lead("LEAD-101")
        self.assertEqual(lead["status"], STATUS_CONVERTED)
        self.assertTrue(lead["is_locked"])

        # Kiểm tra tài khoản khách hàng mới đã có trong DB
        self.assertIsNotNone(lead["converted_account_id"])
        account = db.get_account(lead["converted_account_id"])
        self.assertIsNotNone(account)
        self.assertEqual(account["name"], "Công ty Cổ phần Công nghệ VinTech")

    def test_edit_converted_lead_is_blocked_on_web(self):
        """Kiểm tra cố tình vào sửa lead đã chuyển đổi sẽ bị chặn trên giao diện web"""
        # LEAD-105 là lead đã chuyển đổi sẵn trong dữ liệu demo
        response = self.client.get("/leads/LEAD-105/edit", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Bị chuyển hướng về trang chi tiết kèm flash message
        self.assertIn("ĐÃ BỊ KHÓA BẤT BIẾN".encode("utf-8"), response.data)

    def test_accounts_and_contacts_routes(self):
        response = self.client.get("/accounts")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/contacts")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/opportunities")
        self.assertEqual(response.status_code, 200)

    def test_api_convert_lead(self):
        """Kiểm tra REST API chuyển đổi lead"""
        response = self.client.post("/api/leads/LEAD-102/convert", json={
            "name": "Hợp đồng Bán lẻ An Nam"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["account_id"].startswith("ACC-"))
        self.assertTrue(data["contact_id"].startswith("CON-"))
        self.assertTrue(data["opportunity_id"].startswith("OPP-"))


if __name__ == "__main__":
    unittest.main()
