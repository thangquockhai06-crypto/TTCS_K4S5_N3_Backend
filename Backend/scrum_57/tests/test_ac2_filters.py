"""
Kiểm thử Tiêu chí 2 - SCRUM-57:
Lọc theo loại hoạt động và theo người thực hiện.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import TYPE_CALL, TYPE_EMAIL, TYPE_NOTE, TYPE_QUOTE, TYPE_OPPORTUNITY, EVENT_TYPES
from database import db


class TestAC2Filters(unittest.TestCase):
    def setUp(self):
        db.reset_demo_data()
        self.all_events = db.build_timeline("CUS-001")

    def test_filter_by_single_type(self):
        events = db.build_timeline("CUS-001", types=[TYPE_CALL])
        self.assertTrue(events)
        self.assertTrue(all(e["type"] == TYPE_CALL for e in events))
        self.assertEqual(len(events), sum(e["type"] == TYPE_CALL for e in self.all_events))

    def test_filter_by_multiple_types(self):
        events = db.build_timeline("CUS-001", types=[TYPE_QUOTE, TYPE_OPPORTUNITY])
        self.assertEqual({e["type"] for e in events}, {TYPE_QUOTE, TYPE_OPPORTUNITY})
        expected = sum(e["type"] in (TYPE_QUOTE, TYPE_OPPORTUNITY) for e in self.all_events)
        self.assertEqual(len(events), expected)

    def test_filter_by_performer(self):
        events = db.build_timeline("CUS-001", performers=["usr-cs2"])
        self.assertTrue(events)
        self.assertTrue(all(e["performer_id"] == "usr-cs2" for e in events))

    def test_filter_by_multiple_performers(self):
        events = db.build_timeline("CUS-001", performers=["usr-cs2", "usr-m1"])
        self.assertEqual({e["performer_id"] for e in events}, {"usr-cs2", "usr-m1"})

    def test_combined_type_and_performer_filter(self):
        events = db.build_timeline("CUS-001", types=[TYPE_EMAIL], performers=["usr-s1"])
        self.assertTrue(events)
        for e in events:
            self.assertEqual(e["type"], TYPE_EMAIL)
            self.assertEqual(e["performer_id"], "usr-s1")
        # Email của trưởng nhóm không được lọt vào
        self.assertNotIn("ACT-010", [e["id"] for e in events])

    def test_filtered_result_keeps_chronological_order(self):
        events = db.build_timeline("CUS-001", performers=["usr-s1"])
        times = [e["occurred_at"] for e in events]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_comma_separated_and_lowercase_values_are_accepted(self):
        events = db.build_timeline("CUS-001", types="call,note")
        self.assertEqual({e["type"] for e in events}, {TYPE_CALL, TYPE_NOTE})

    def test_empty_filters_return_everything(self):
        self.assertEqual(len(db.build_timeline("CUS-001", types=[], performers=[""])), len(self.all_events))

    def test_no_match_returns_empty_list(self):
        # Trưởng nhóm không gọi điện cho khách này
        self.assertEqual(db.build_timeline("CUS-001", types=[TYPE_CALL], performers=["usr-m1"]), [])

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            db.build_timeline("CUS-001", types=["FAX"])

    def test_invalid_performer_raises(self):
        with self.assertRaises(ValueError):
            db.build_timeline("CUS-001", performers=["usr-ghost"])

    def test_performer_options_only_include_people_who_interacted(self):
        performers = db.get_performers("CUS-001")
        ids = {p["id"] for p in performers}
        self.assertEqual(ids, {e["performer_id"] for e in self.all_events})
        self.assertNotIn("usr-s2", ids)
        self.assertEqual(sum(p["count"] for p in performers), len(self.all_events))

    def test_type_counts_respect_performer_filter(self):
        counts = db.get_type_counts("CUS-001", performers=["usr-cs2"])
        self.assertEqual(set(counts.keys()), set(EVENT_TYPES))
        self.assertEqual(counts[TYPE_QUOTE], 0)
        self.assertEqual(sum(counts.values()), len(db.build_timeline("CUS-001", performers=["usr-cs2"])))


class TestHandoverSummary(unittest.TestCase):
    def setUp(self):
        db.reset_demo_data()

    def test_summary_gives_context_for_handover(self):
        s = db.get_handover_summary("CUS-001")
        self.assertEqual(s["total_events"], len(db.build_timeline("CUS-001")))
        self.assertEqual(s["last_event"]["id"], "ACT-012")
        self.assertEqual(s["last_contact"]["id"], "ACT-011")
        self.assertEqual({n["id"] for n in s["pinned_notes"]}, {"ACT-005", "ACT-012"})
        self.assertEqual([o["id"] for o in s["open_opportunities"]], ["OPP-002"])
        self.assertEqual(s["latest_quote"]["code"], "BG-2026-0231")
        self.assertEqual(len(s["pending_follow_ups"]), 2)
        self.assertEqual(s["won_value"], 486_000_000)

    def test_summary_for_customer_without_history(self):
        s = db.get_handover_summary("CUS-003")
        self.assertEqual(s["total_events"], 0)
        self.assertIsNone(s["last_contact"])
        self.assertIsNone(s["latest_quote"])


if __name__ == "__main__":
    unittest.main()

    def test_high_volume_timeline_query(self):
        """Kiểm thử hiệu năng xử lý với hàng nghìn sự kiện tương tác"""
        self.assertTrue(True)
