"""
Kiểm thử Tiêu chí 2 (Acceptance Criteria 2) - Ticket SCRUM-99:
"Lọc theo khoảng thời gian"
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database


class TestAC2DateRangeFilter(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_parse_date_range_presets(self):
        """Kiểm tra phân giải các mốc lọc thời gian phổ biến"""
        # Hôm nay
        f_today, t_today = self.db.parse_date_range(preset="today")
        self.assertIsNotNone(f_today)
        self.assertIsNotNone(t_today)
        self.assertEqual(f_today.date(), datetime.now().date())

        # 7 ngày qua
        f_7, t_7 = self.db.parse_date_range(preset="last_7_days")
        self.assertAlmostEqual((t_7 - f_7).days, 7, delta=1)

        # 30 ngày qua
        f_30, t_30 = self.db.parse_date_range(preset="last_30_days")
        self.assertAlmostEqual((t_30 - f_30).days, 30, delta=1)

        # Toàn bộ thời gian
        f_all, t_all = self.db.parse_date_range(preset="all")
        self.assertIsNone(f_all)
        self.assertIsNone(t_all)

    def test_filter_leads_by_last_7_days(self):
        """
        Chứng minh khi lọc 7 ngày gần nhất:
        - Số lượng lead trả về phải nhỏ hơn hoặc bằng toàn bộ thời gian
        - Mọi lead trong danh sách đều có created_at >= (now - 7 days)
        """
        all_leads = self.db.get_leads_filtered()
        f_7, t_7 = self.db.parse_date_range(preset="last_7_days")
        leads_7 = self.db.get_leads_filtered(from_dt=f_7, to_dt=t_7)

        self.assertLess(len(leads_7), len(all_leads))
        for l in leads_7:
            self.assertGreaterEqual(l["created_at"], f_7)
            self.assertLessEqual(l["created_at"], t_7)

    def test_report_metrics_update_when_date_range_changes(self):
        """
        Chứng minh khi áp dụng bộ lọc thời gian hẹp hơn:
        Số lead và tổng doanh thu tính toán trong báo cáo nguồn lead
        phải giảm tương ứng, phản ánh chính xác khoảng thời gian được chọn.
        """
        # Báo cáo toàn bộ thời gian
        report_all = self.db.get_report_by_source()
        total_leads_all = sum(s["total_leads"] for s in report_all)
        total_rev_all = sum(s["actual_revenue"] for s in report_all)

        # Báo cáo 7 ngày qua
        f_7, t_7 = self.db.parse_date_range(preset="last_7_days")
        report_7 = self.db.get_report_by_source(from_dt=f_7, to_dt=t_7)
        total_leads_7 = sum(s["total_leads"] for s in report_7)
        total_rev_7 = sum(s["actual_revenue"] for s in report_7)

        self.assertGreater(total_leads_all, total_leads_7)
        self.assertGreaterEqual(total_rev_all, total_rev_7)

    def test_custom_date_range_filtering(self):
        """Kiểm tra lọc tùy biến ngày bắt đầu và kết thúc"""
        from_str = "2026-02-01"
        to_str = "2026-02-28"
        f_custom, t_custom = self.db.parse_date_range(from_date_str=from_str, to_date_str=to_str)
        
        self.assertEqual(f_custom.strftime("%Y-%m-%d"), from_str)
        self.assertEqual(t_custom.strftime("%Y-%m-%d"), to_str)

        filtered = self.db.get_leads_filtered(from_dt=f_custom, to_dt=t_custom)
        for l in filtered:
            self.assertTrue(f_custom <= l["created_at"] <= t_custom)


if __name__ == "__main__":
    unittest.main()
