"""
Kiểm thử tích hợp các Web Routes & API - Ticket SCRUM-99
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import db


class TestWebRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        db.reset_demo_data()

    def test_report_view_get(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("SCRUM-99".encode("utf-8"), response.data)
        self.assertIn("Báo Cáo Hiệu Quả Từng Nguồn Lead".encode("utf-8"), response.data)

    def test_report_with_date_preset_filter(self):
        response = self.client.get("/report?preset=last_7_days")
        self.assertEqual(response.status_code, 200)
        self.assertIn("7 ngày gần nhất".encode("utf-8"), response.data)

    def test_export_excel_endpoint(self):
        """Kiểm tra tải file Excel trực tiếp qua route /export/excel"""
        response = self.client.get("/export/excel?preset=all")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertIn("attachment; filename=", response.headers.get("Content-Disposition", ""))
        self.assertTrue(len(response.data) > 1000)

    def test_campaigns_view_get(self):
        response = self.client.get("/campaigns")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Google Search".encode("utf-8"), response.data)

    def test_leads_view_get(self):
        response = self.client.get("/leads")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Danh Sách Lead".encode("utf-8"), response.data)

    def test_api_report_endpoints(self):
        res_source = self.client.get("/api/report/source")
        self.assertEqual(res_source.status_code, 200)
        self.assertTrue(res_source.get_json()["success"])

        res_camp = self.client.get("/api/report/campaign")
        self.assertEqual(res_camp.status_code, 200)
        self.assertTrue(res_camp.get_json()["success"])

        res_sum = self.client.get("/api/report/summary")
        self.assertEqual(res_sum.status_code, 200)
        self.assertTrue(res_sum.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
