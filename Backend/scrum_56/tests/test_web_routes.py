"""
Kiểm thử tích hợp các Web Routes & API - Ticket SCRUM-56
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

    def test_leads_list_default_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("SCRUM-56".encode("utf-8"), response.data)
        self.assertIn("Bộ Lọc Lưu Sẵn".encode("utf-8"), response.data)

    def test_leads_list_with_saved_filter_id(self):
        response = self.client.get("/leads?filter_id=sf-sla-alert")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Quá Hạn SLA".encode("utf-8"), response.data)

    def test_saved_filter_create_post(self):
        response = self.client.post("/saved-filters/create", data={
            "name": "Bộ lọc test tự động",
            "icon": "🧪",
            "temperature": "HOT",
            "source": "Google Ads"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Bộ lọc test tự động".encode("utf-8"), response.data)

    def test_lead_record_call_post(self):
        response = self.client.post("/leads/LEAD-101/call", data={
            "notes": "Đã trao đổi tư vấn qua điện thoại",
            "next_call_date": "2026-10-15"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("hoàn thành cam kết SLA".encode("utf-8"), response.data)

    def test_api_endpoints(self):
        res_leads = self.client.get("/api/leads?temperature=HOT")
        self.assertEqual(res_leads.status_code, 200)
        self.assertTrue(res_leads.get_json()["success"])

        res_filters = self.client.get("/api/saved-filters")
        self.assertEqual(res_filters.status_code, 200)
        self.assertTrue(res_filters.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
