"""
Kiểm thử Tích hợp Web Routes & REST APIs - Ticket SCRUM-33:
Kiểm tra toàn diện tất cả các trang giao diện, bộ lọc, điều hướng và API
"""

import sys
import os
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import db
from config import (
    STATUS_APPROVED,
    STATUS_PENDING_APPROVAL,
    ACTION_APPROVE,
    ACTION_REJECT,
    ACTION_REQUEST_CHANGES
)


class TestWebRoutesAndAPIs(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        db.reset_demo_data()

    def test_dashboard_route_loads(self):
        """Kiểm tra trang Dashboard Bàn làm việc tải thành công HTTP 200"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("SCRUM-33".encode("utf-8"), response.data)
        self.assertIn("Duyệt Báo Giá".encode("utf-8"), response.data)

    def test_approval_queue_route_with_filters(self):
        """Kiểm tra trang Hàng chờ duyệt và các bộ lọc thẩm quyền"""
        # Tất cả
        resp_all = self.client.get("/approval-queue")
        self.assertEqual(resp_all.status_code, 200)

        # Lọc Trưởng nhóm duyệt
        resp_tl = self.client.get("/approval-queue?authority=TEAM_LEAD")
        self.assertEqual(resp_tl.status_code, 200)

        # Lọc Giám đốc duyệt
        resp_dir = self.client.get("/approval-queue?authority=DIRECTOR")
        self.assertEqual(resp_dir.status_code, 200)

        # Lọc Dưới giá sàn
        resp_floor = self.client.get("/approval-queue?authority=BELOW_FLOOR")
        self.assertEqual(resp_floor.status_code, 200)

    def test_quote_detail_route(self):
        """Kiểm tra trang chi tiết báo giá và hiển thị lịch sử duyệt"""
        response = self.client.get("/quotes/Q-302")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Q-302".encode("utf-8"), response.data)

    def test_quote_action_approve_route(self):
        """Kiểm tra hành động Duyệt báo giá qua form POST"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "usr-03" # Trưởng nhóm

        response = self.client.post("/quotes/Q-302/action", data={
            "action": ACTION_APPROVE,
            "comment": "Đồng ý mức chiết khấu này."
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Kiểm tra trạng thái báo giá đã chuyển sang APPROVED
        q = db.get_quote("Q-302")
        self.assertEqual(q["status"], STATUS_APPROVED)

    def test_quote_action_reject_route_validates_comment(self):
        """Kiểm tra hành động Từ chối bắt buộc có ý kiến"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "usr-03"

        # Gửi ý kiến rỗng -> Bị cảnh báo lỗi
        response = self.client.post("/quotes/Q-302/action", data={
            "action": ACTION_REJECT,
            "comment": "   "
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("BẮT BUỘC".encode("utf-8"), response.data)

        # Báo giá không bị chuyển trạng thái
        q = db.get_quote("Q-302")
        self.assertEqual(q["status"], STATUS_PENDING_APPROVAL)

    def test_quote_send_route_strictly_enforces_approved_status(self):
        """Kiểm tra route gửi khách hàng: chỉ duyệt mới được gửi"""
        # Thử gửi Q-302 (chưa duyệt) -> Bị từ chối
        resp_fail = self.client.post("/quotes/Q-302/send", follow_redirects=True)
        self.assertEqual(resp_fail.status_code, 200)
        self.assertIn("CHỈ BÁO GIÁ ĐÃ PHÊ DUYỆT".encode("utf-8"), resp_fail.data)

        # Gửi Q-301 (đã duyệt) -> Thành công
        resp_ok = self.client.post("/quotes/Q-301/send", follow_redirects=True)
        self.assertEqual(resp_ok.status_code, 200)
        self.assertIn("thành công".encode("utf-8"), resp_ok.data)

    def test_api_calculate_discount(self):
        """Kiểm tra REST API tính toán chiết khấu thời gian thực"""
        payload = {
            "items": [
                {
                    "product_id": "PRD-001",
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 15.0
                }
            ]
        }
        resp = self.client.post(
            "/api/calculate-discount",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["calculation"]["discount_rate"], 15.0)
        self.assertEqual(data["calculation"]["approval_authority"], "TEAM_LEAD")

    def test_api_get_history(self):
        """Kiểm tra REST API lấy sổ cái lịch sử duyệt bất biến"""
        resp = self.client.get("/api/quotes/Q-305/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["is_immutable"])
        self.assertGreaterEqual(len(data["history"]), 2)

    def test_switch_persona_and_reset_data(self):
        """Kiểm tra tính năng chuyển đổi Persona và khôi phục dữ liệu"""
        resp_switch = self.client.get("/switch-persona/usr-04", follow_redirects=True)
        self.assertEqual(resp_switch.status_code, 200)

        resp_reset = self.client.post("/reset-data", follow_redirects=True)
        self.assertEqual(resp_reset.status_code, 200)


if __name__ == "__main__":
    unittest.main()
