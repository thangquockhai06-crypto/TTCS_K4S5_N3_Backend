"""
Unit Test - Kiểm thử toàn diện Web Routes & REST APIs (SCRUM-35 / SCRUM-37)
Subtasks: SCRUM-234 (FE) & SCRUM-235 (BE)
"""

import unittest
import json
from app import app
from database import db


class TestWebRoutesAndAPIs(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_dashboard_route(self):
        """Kiểm tra trang Dashboard trả về mã 200 và chứa thông tin cần thiết"""
        res = self.app.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("AutoLead CRM".encode("utf-8"), res.data)
        self.assertIn("SCRUM-37".encode("utf-8"), res.data)

    def test_quotes_list_route(self):
        """Kiểm tra trang danh sách báo giá"""
        res = self.app.get("/quotes")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Danh Sách Họ Báo Giá".encode("utf-8"), res.data)

    def test_quote_detail_route(self):
        """Kiểm tra trang chi tiết báo giá mẫu BG-2026-001"""
        res = self.app.get("/quotes/BG-2026-001")
        self.assertEqual(res.status_code, 200)
        self.assertIn("BG-2026-001".encode("utf-8"), res.data)
        self.assertIn("CÂY PHIÊN BẢN BÁO GIÁ".encode("utf-8"), res.data)

    def test_quote_compare_route(self):
        """Kiểm tra trang so sánh cạnh nhau 2 phiên bản (AC2)"""
        family = db.get_quote_family("BG-2026-001")
        if len(family) >= 2:
            v1_id = family[0]["version_id"]
            v2_id = family[1]["version_id"]
            res = self.app.get(f"/quotes/BG-2026-001/compare?v1={v1_id}&v2={v2_id}")
            self.assertEqual(res.status_code, 200)
            self.assertIn("So Sánh Cạnh Nhau Hai Phiên Bản".encode("utf-8"), res.data)
            self.assertIn("TỔNG THANH TOÁN CUỐI".encode("utf-8"), res.data)

    def test_api_create_quote(self):
        """Kiểm tra API tạo báo giá mới (POST /api/quotes)"""
        payload = {
            "title": "Báo Giá Thử Nghiệm API",
            "customer_name": "Công ty API Client",
            "customer_email": "api@client.vn",
            "validity_days": 20,
            "items": [
                {
                    "product_id": "PROD-CRM-ENT",
                    "product_name": "CRM Enterprise",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 0.0
                }
            ],
            "is_sent": False
        }
        res = self.app.post("/api/quotes", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["version_number"], 1)

    def test_api_compare_versions(self):
        """Kiểm tra API so sánh phiên bản (GET /api/quotes/compare)"""
        family = db.get_quote_family("BG-2026-001")
        v1_id = family[0]["version_id"]
        v2_id = family[1]["version_id"]

        res = self.app.get(f"/api/quotes/compare?v1={v1_id}&v2={v2_id}")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("items_diff", data["diff"])
        self.assertIn("financial_diff", data["diff"])

    def test_api_simulator_run(self):
        """Kiểm tra API chạy bộ mô phỏng 3 Acceptance Criteria (POST /api/simulator/run)"""
        res = self.app.post("/api/simulator/run")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertTrue(data["all_passed"], "Toàn bộ 3 tiêu chí trong simulator phải đạt 100%!")
        self.assertEqual(len(data["results"]), 3)


if __name__ == "__main__":
    unittest.main()
