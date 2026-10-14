"""
Kiểm thử tích hợp Web Routes & REST API - Ticket SCRUM-57
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import db


class TestWebRoutes(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        db.reset_demo_data()

    def test_customer_list_page(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("SCRUM-57".encode(), res.data)
        self.assertIn("Sen Vàng".encode(), res.data)

    def test_customer_search(self):
        res = self.client.get("/customers", query_string={"search": "nhà thuốc"})
        self.assertIn("An Khang".encode(), res.data)
        self.assertNotIn("Sen Vàng".encode(), res.data)

    def test_timeline_page_renders_all_sources(self):
        res = self.client.get("/customers/CUS-001/timeline")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode()
        self.assertIn("Bối cảnh trong 5 phút", html)
        for event_id in ("event-ACT-001", "event-OPC-005", "event-QUO-002"):
            self.assertIn(event_id, html)

    def test_timeline_page_with_filters(self):
        res = self.client.get("/customers/CUS-001/timeline?type=QUOTE_SENT&performer=usr-s1")
        html = res.data.decode()
        self.assertIn("event-QUO-001", html)
        self.assertNotIn("event-ACT-001", html)
        self.assertNotIn("event-OPC-001", html)

    def test_timeline_page_ignores_invalid_filter(self):
        res = self.client.get("/customers/CUS-001/timeline?type=FAX")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Đã bỏ qua bộ lọc không hợp lệ".encode(), res.data)
        self.assertIn(b"event-ACT-001", res.data)

    def test_unknown_customer_redirects(self):
        res = self.client.get("/customers/CUS-999/timeline", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Không tìm thấy khách hàng CUS-999".encode(), res.data)

    def test_add_activity(self):
        res = self.client.post("/customers/CUS-001/activities", data={
            "type": "NOTE", "subject": "Đã tiếp nhận khách từ Minh Tâm", "content": "Sẽ gọi chị Hồng sau 14h"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Đã tiếp nhận khách từ Minh Tâm".encode(), res.data)

    def test_add_activity_requires_subject(self):
        res = self.client.post("/customers/CUS-001/activities", data={"type": "NOTE", "subject": " "},
                               follow_redirects=True)
        self.assertIn("Vui lòng nhập tiêu đề".encode(), res.data)

    def test_api_timeline(self):
        res = self.client.get("/api/customers/CUS-001/timeline?type=CALL&type=EMAIL&order=asc")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["filters"]["types"], ["CALL", "EMAIL"])
        self.assertTrue(all(e["type"] in ("CALL", "EMAIL") for e in data["events"]))
        times = [e["occurred_at"] for e in data["events"]]
        self.assertEqual(times, sorted(times))

    def test_api_timeline_errors(self):
        self.assertEqual(self.client.get("/api/customers/CUS-999/timeline").status_code, 404)
        self.assertEqual(self.client.get("/api/customers/CUS-001/timeline?type=FAX").status_code, 400)
        self.assertEqual(self.client.get("/api/customers/CUS-001/timeline?performer=x").status_code, 400)
        self.assertEqual(self.client.get("/api/customers/CUS-001/timeline?order=zzz").status_code, 400)

    def test_api_summary_and_customers(self):
        res = self.client.get("/api/customers/CUS-001/summary")
        data = res.get_json()
        self.assertEqual(data["latest_quote"]["code"], "BG-2026-0231")
        self.assertEqual(len(data["pending_follow_ups"]), 2)

        res = self.client.get("/api/customers")
        self.assertEqual(res.get_json()["count"], 4)


if __name__ == "__main__":
    unittest.main()
