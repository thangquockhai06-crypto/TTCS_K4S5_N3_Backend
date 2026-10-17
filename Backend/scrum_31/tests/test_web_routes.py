"""
Kiểm thử Tích Hợp (Integration Tests) - Toàn bộ Web Routes & APIs (SCRUM-31)
"""

import sys
import os
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import db


class TestWebRoutes(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        db.reset_demo_data()

    def test_dashboard_route(self):
        """Kiểm tra màn hình Dashboard"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("SCRUM-31".encode("utf-8"), response.data)
        self.assertIn("Bàn Làm Việc".encode("utf-8"), response.data)

    def test_opportunities_list_route(self):
        """Kiểm tra màn hình danh sách cơ hội"""
        response = self.client.get("/opportunities")
        self.assertEqual(response.status_code, 200)
        self.assertIn("OPP-401".encode("utf-8"), response.data)

    def test_quotes_list_route(self):
        """Kiểm tra màn hình danh sách báo giá"""
        response = self.client.get("/quotes")
        self.assertEqual(response.status_code, 200)
        self.assertIn("BG-2026-0501".encode("utf-8"), response.data)

    def test_quote_detail_route(self):
        """Kiểm tra màn hình chi tiết báo giá"""
        response = self.client.get("/quotes/QUOTE-501")
        self.assertEqual(response.status_code, 200)
        self.assertIn("QUOTE-501".encode("utf-8"), response.data)
        self.assertIn("Logistics Đại Nam".encode("utf-8"), response.data)

    def test_quote_edit_route(self):
        """Kiểm tra màn hình chỉnh sửa báo giá nháp"""
        response = self.client.get("/quotes/QUOTE-501/edit")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Chỉnh Sửa Báo Giá".encode("utf-8"), response.data)

    def test_quote_create_get_route(self):
        """Kiểm tra màn hình soạn báo giá mới từ cơ hội"""
        response = self.client.get("/quotes/new/OPP-401")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dược Phẩm An Bình".encode("utf-8"), response.data)
        self.assertIn("AutoLead CRM Enterprise".encode("utf-8"), response.data)

    def test_simulator_page_and_api(self):
        """Kiểm tra trang Simulator và API kiểm thử tự động 5 tiêu chí"""
        page_res = self.client.get("/simulator")
        self.assertEqual(page_res.status_code, 200)
        self.assertIn("Trình Kiểm Thử & Chấm Điểm 5 Tiêu Chí".encode("utf-8"), page_res.data)

        # Gọi API kiểm thử
        api_res = self.client.get("/api/run-simulator-tests")
        self.assertEqual(api_res.status_code, 200)
        data = json.loads(api_res.data)
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 5)
        for res in data["results"]:
            self.assertEqual(res["status"], "PASSED")

    def test_calculate_line_api(self):
        """Kiểm tra API tính toán dòng sản phẩm tức thời"""
        payload = {
            "quantity": 2,
            "unit_price": 5000000,
            "discount_type": "PERCENT",
            "discount_value": 10.0
        }
        res = self.client.post(
            "/api/calculate-line",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["subtotal"], 10000000.0)
        self.assertEqual(data["discount_amount"], 1000000.0)
        self.assertEqual(data["total"], 9000000.0)


if __name__ == "__main__":
    unittest.main()
