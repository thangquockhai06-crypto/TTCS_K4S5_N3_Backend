"""
Kiểm thử Tiêu chí 1 - SCRUM-57:
Gộp toàn bộ hoạt động, thay đổi cơ hội, báo giá đã gửi theo thứ tự thời gian.
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import (
    SOURCE_ACTIVITY,
    SOURCE_OPPORTUNITY,
    SOURCE_QUOTE,
    TYPE_NOTE,
    TYPE_OPPORTUNITY,
    TYPE_QUOTE,
    ORDER_ASC,
    ORDER_DESC,
)
from database import db


class TestAC1MergedTimeline(unittest.TestCase):
    def setUp(self):
        db.reset_demo_data()

    def _expected_count(self, customer_id):
        acts = [a for a in db.activities if a["customer_id"] == customer_id]
        opp_ids = {o["id"] for o in db.opportunities.values() if o["customer_id"] == customer_id}
        changes = [c for c in db.opportunity_changes if c["opportunity_id"] in opp_ids]
        quotes = [q for q in db.quotes if q["customer_id"] == customer_id]
        return len(acts), len(changes), len(quotes)

    def test_timeline_contains_all_three_sources(self):
        events = db.build_timeline("CUS-001")
        n_act, n_opp, n_quote = self._expected_count("CUS-001")

        self.assertEqual(len(events), n_act + n_opp + n_quote)
        sources = {e["source"] for e in events}
        self.assertEqual(sources, {SOURCE_ACTIVITY, SOURCE_OPPORTUNITY, SOURCE_QUOTE})
        self.assertEqual(sum(e["source"] == SOURCE_OPPORTUNITY for e in events), n_opp)
        self.assertEqual(sum(e["source"] == SOURCE_QUOTE for e in events), n_quote)

    def test_default_order_is_newest_first(self):
        events = db.build_timeline("CUS-001")
        times = [e["occurred_at"] for e in events]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_ascending_order_is_oldest_first(self):
        events = db.build_timeline("CUS-001", order=ORDER_ASC)
        times = [e["occurred_at"] for e in events]
        self.assertEqual(times, sorted(times))
        # Thứ tự tăng dần phải đúng bằng đảo ngược của thứ tự giảm dần
        desc_ids = [e["id"] for e in db.build_timeline("CUS-001", order=ORDER_DESC)]
        self.assertEqual([e["id"] for e in events], list(reversed(desc_ids)))

    def test_sources_are_interleaved_by_time_not_grouped(self):
        """Báo giá & thay đổi cơ hội phải xen kẽ giữa các hoạt động theo đúng thời điểm."""
        events = db.build_timeline("CUS-001", order=ORDER_ASC)
        ids = [e["id"] for e in events]
        # Báo giá đầu tiên (QUO-001) gửi sau buổi demo ACT-002 và trước email ACT-003
        self.assertLess(ids.index("ACT-002"), ids.index("QUO-001"))
        self.assertLess(ids.index("QUO-001"), ids.index("ACT-003"))
        # Cơ hội chuyển "Thắng" (OPC-005) sau khi báo giá QUO-002 được gửi
        self.assertLess(ids.index("QUO-002"), ids.index("OPC-005"))

    def test_events_have_normalized_fields(self):
        required = {"id", "source", "type", "type_label", "icon", "occurred_at",
                    "performer_id", "performer", "title", "summary", "details"}
        for e in db.build_timeline("CUS-001"):
            self.assertTrue(required.issubset(e.keys()), f"Thiếu trường ở {e['id']}")
            self.assertIsInstance(e["occurred_at"], datetime)
            self.assertTrue(e["title"])

    def test_opportunity_and_quote_events_are_described(self):
        events = {e["id"]: e for e in db.build_timeline("CUS-001")}
        stage = events["OPC-005"]
        self.assertEqual(stage["type"], TYPE_OPPORTUNITY)
        self.assertIn("Đàm phán", stage["title"])
        self.assertIn("Thắng", stage["title"])
        self.assertTrue(stage["is_won"])

        amount = events["OPC-003"]
        self.assertIn("522.000.000", amount["title"])
        self.assertIn("486.000.000", amount["title"])

        quote = events["QUO-002"]
        self.assertEqual(quote["type"], TYPE_QUOTE)
        self.assertIn("BG-2026-0167", quote["title"])
        self.assertEqual(quote["quote_status"], "ACCEPTED")

    def test_timeline_only_contains_the_requested_customer(self):
        events = db.build_timeline("CUS-002")
        ids = {e["id"] for e in events}
        self.assertTrue(ids)
        self.assertFalse(any(i in ids for i in ("ACT-001", "OPC-001", "QUO-001")))

    def test_customer_without_interactions_returns_empty(self):
        self.assertEqual(db.build_timeline("CUS-003"), [])

    def test_unknown_customer_raises(self):
        with self.assertRaises(KeyError):
            db.build_timeline("CUS-999")

    def test_invalid_order_raises(self):
        with self.assertRaises(ValueError):
            db.build_timeline("CUS-001", order="random")

    def test_new_activity_appears_at_top(self):
        db.add_activity("CUS-001", TYPE_NOTE, "Đã tiếp nhận khách", "Tiếp nhận từ Minh Tâm", "usr-cs1")
        top = db.build_timeline("CUS-001")[0]
        self.assertEqual(top["title"], "Đã tiếp nhận khách")
        self.assertEqual(top["performer_id"], "usr-cs1")

    def test_group_by_day_preserves_order(self):
        events = db.build_timeline("CUS-001")
        groups = db.group_by_day(events)
        flattened = [e["id"] for g in groups for e in g["events"]]
        self.assertEqual(flattened, [e["id"] for e in events])
        dates = [g["date"] for g in groups]
        self.assertEqual(len(dates), len(set(dates)))


if __name__ == "__main__":
    unittest.main()
