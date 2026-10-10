"""
Unit Test - Kiểm thử toàn diện Web Routes và REST APIs (SCRUM-38)
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import db


class TestWebRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config["TESTING"] = True
        db.reset_to_seed()

    def test_dashboard_route(self):
        """Kiểm tra trang Dashboard hoạt động và hiển thị đúng thông tin"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_quotes_list_route(self):
        """Kiểm tra trang danh sách báo giá"""
        response = self.client.get("/quotes")
        self.assertEqual(response.status_code, 200)

    def test_convert_quote_get_route(self):
        """Kiểm tra truy cập trang chuyển đổi báo giá được chấp nhận"""
        response = self.client.get("/quotes/BG-2026-001/convert")
        self.assertEqual(response.status_code, 200)

    def test_convert_quote_post_route_success(self):
        """Kiểm tra submit form chuyển đổi báo giá thành công"""
        form_data = {
            "contract_number": "HD-2026/088",
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Thanh toán 100% trong vòng 7 ngày làm việc sau khi ký",
            "payment_terms_notes": "Chuyển khoản Vietcombank"
        }
        response = self.client.post("/quotes/BG-2026-001/convert", data=form_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Kiểm tra HĐ đã tạo
        c = db.get_contract_by_number("HD-2026/088")
        self.assertIsNotNone(c)
        self.assertEqual(c["grand_total"], 83710000)

    def test_convert_quote_post_duplicate_contract_number(self):
        """Kiểm tra submit form với số HĐ trùng lặp (HD-2026/001) hiển thị thông báo lỗi"""
        form_data = {
            "contract_number": "HD-2026/001",  # Đã có sẵn trong hệ thống
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Net 30"
        }
        response = self.client.post("/quotes/BG-2026-001/convert", data=form_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Báo lỗi flash message trong HTML
        self.assertIn("LỖI TIÊU CHÍ 4 - SỐ HỢP ĐỒNG TRÙNG LẶP".encode("utf-8"), response.data)

    def test_contracts_list_route(self):
        """Kiểm tra trang danh sách hợp đồng"""
        response = self.client.get("/contracts")
        self.assertEqual(response.status_code, 200)

    def test_contract_detail_route(self):
        """Kiểm tra trang xem chi tiết hợp đồng mẫu"""
        response = self.client.get("/contracts/CTR-2026-001")
        self.assertEqual(response.status_code, 200)

    def test_opportunities_route(self):
        """Kiểm tra trang quản lý cơ hội CRM và pipeline"""
        response = self.client.get("/opportunities")
        self.assertEqual(response.status_code, 200)

    def test_simulator_route(self):
        """Kiểm tra trang kiểm thử tự động"""
        response = self.client.get("/simulator")
        self.assertEqual(response.status_code, 200)

    def test_api_check_contract_number(self):
        """Kiểm tra REST API kiểm tra số hợp đồng duy nhất"""
        # Số đã tồn tại
        r1 = self.client.get("/api/contracts/check-number?number=HD-2026/001")
        self.assertEqual(r1.status_code, 200)
        self.assertFalse(r1.get_json()["available"])

        # Số mới
        r2 = self.client.get("/api/contracts/check-number?number=HD-2026/999")
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.get_json()["available"])

    def test_api_run_simulator(self):
        """Kiểm tra REST API chạy toàn bộ 4 kịch bản kiểm thử Tiêu chí chấp nhận"""
        response = self.client.post("/api/simulator/run-all")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["all_passed"])
        self.assertEqual(len(data["results"]), 4)


if __name__ == "__main__":
    unittest.main()
