"""
Kiểm thử Tiêu chí 1 (Acceptance Criteria 1) - Ticket SCRUM-56:
"Lọc theo trạng thái, nguồn, phân loại nóng ấm lạnh, người phụ trách, khoảng thời gian"
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import (
    Database,
    STATUS_IN_CARE,
    STATUS_ASSIGNED,
    TEMP_HOT,
    TEMP_WARM,
    TEMP_COLD
)


class TestAC1MultiCriteriaFilter(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_filter_by_status(self):
        """Chứng minh lọc chính xác theo trạng thái lead"""
        leads_in_care = self.db.filter_leads({"status": STATUS_IN_CARE})
        self.assertGreater(len(leads_in_care), 0)
        for l in leads_in_care:
            self.assertEqual(l["status"], STATUS_IN_CARE)

    def test_filter_by_source(self):
        """Chứng minh lọc chính xác theo nguồn lead"""
        leads_google = self.db.filter_leads({"source": "Google Ads"})
        self.assertGreater(len(leads_google), 0)
        for l in leads_google:
            self.assertEqual(l["source"], "Google Ads")

    def test_filter_by_temperature(self):
        """Chứng minh lọc chính xác theo phân loại Nóng / Ấm / Lạnh (HOT / WARM / COLD)"""
        # 1. Lọc lead NÓNG (HOT)
        leads_hot = self.db.filter_leads({"temperature": TEMP_HOT})
        self.assertGreater(len(leads_hot), 0)
        for l in leads_hot:
            self.assertEqual(l["temperature"], TEMP_HOT)

        # 2. Lọc lead ẤM (WARM)
        leads_warm = self.db.filter_leads({"temperature": TEMP_WARM})
        self.assertGreater(len(leads_warm), 0)
        for l in leads_warm:
            self.assertEqual(l["temperature"], TEMP_WARM)

        # 3. Lọc lead LẠNH (COLD)
        leads_cold = self.db.filter_leads({"temperature": TEMP_COLD})
        self.assertGreater(len(leads_cold), 0)
        for l in leads_cold:
            self.assertEqual(l["temperature"], TEMP_COLD)

    def test_filter_by_assigned_to(self):
        """Chứng minh lọc theo người phụ trách (Tôi phụ trách vs Chưa phân bổ)"""
        # Lead của tôi (usr-01: Nguyễn Văn Tuấn)
        my_leads = self.db.filter_leads({"assigned_to": "mine"}, user_id="usr-01")
        self.assertGreater(len(my_leads), 0)
        for l in my_leads:
            self.assertEqual(l["assigned_to_id"], "usr-01")

        # Lead chưa phân bổ
        unassigned = self.db.filter_leads({"assigned_to": "unassigned"})
        self.assertGreater(len(unassigned), 0)
        for l in unassigned:
            self.assertIsNone(l["assigned_to_id"])

    def test_filter_by_date_range(self):
        """Chứng minh lọc theo khoảng thời gian tạo lead"""
        leads_7_days = self.db.filter_leads({"date_preset": "last_7_days"})
        now = datetime.now()
        for l in leads_7_days:
            self.assertGreaterEqual(l["created_at"], now - timedelta(days=7))

    def test_combined_multi_criteria_filter(self):
        """
        Chứng minh khả năng kết hợp đồng thời nhiều tiêu chí:
        Nguồn 'Google Ads' + Nhiệt độ 'HOT' + Người phụ trách 'mine'
        """
        criteria = {
            "source": "Google Ads",
            "temperature": TEMP_HOT,
            "assigned_to": "mine"
        }
        filtered = self.db.filter_leads(criteria, user_id="usr-01")
        self.assertGreater(len(filtered), 0)
        for l in filtered:
            self.assertEqual(l["source"], "Google Ads")
            self.assertEqual(l["temperature"], TEMP_HOT)
            self.assertEqual(l["assigned_to_id"], "usr-01")


if __name__ == "__main__":
    unittest.main()
