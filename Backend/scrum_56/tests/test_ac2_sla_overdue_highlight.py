"""
Kiểm thử Tiêu chí 2 (Acceptance Criteria 2) - Ticket SCRUM-56:
"Lead quá SLA hiển thị nổi bật"
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database, SLA_OVERDUE


class TestAC2SLAOverdueHighlight(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_overdue_sla_detection_and_flagging(self):
        """
        Chứng minh hệ thống tự động phát hiện lead đã quá hạn SLA:
        1. Gắn nhãn SLA_OVERDUE và cờ is_overdue = True
        2. Tính toán chính xác thời gian trễ hiển thị bằng tiếng Việt
        """
        lead_101 = self.db.leads.get("LEAD-101")
        self.assertIsNotNone(lead_101)

        sla_info = self.db.calculate_sla_status(lead_101)
        self.assertTrue(sla_info["is_overdue"])
        self.assertEqual(sla_info["status"], SLA_OVERDUE)
        self.assertEqual(sla_info["badge_class"], "badge-red")
        self.assertIn("Quá hạn", sla_info["delay_text"])

    def test_filter_only_sla_overdue_leads(self):
        """
        Chứng minh bộ lọc chuyên biệt cho lead quá SLA:
        Chỉ trả về các lead đang bị vi phạm SLA chưa được xử lý.
        """
        overdue_leads = self.db.filter_leads({"is_sla_overdue": True})
        self.assertGreater(len(overdue_leads), 0)

        for l in overdue_leads:
            self.assertTrue(l["sla"]["is_overdue"])
            self.assertIsNone(l.get("contacted_at"))
            self.assertLess(l["sla_deadline"], datetime.now())

    def test_overdue_leads_are_prioritized_at_top_of_list(self):
        """
        Chứng minh lead quá hạn SLA được xếp nổi bật lên đầu danh sách
        để nhân viên mở máy là nhìn thấy ngay lập tức.
        """
        all_filtered = self.db.filter_leads({})
        first_lead = all_filtered[0]
        self.assertTrue(
            first_lead["sla"]["is_overdue"],
            "Lead đầu tiên trong danh sách mặc định phải là lead quá hạn SLA cần xử lý khẩn cấp!"
        )

    def test_record_call_resolves_overdue_sla_status(self):
        """
        Chứng minh khi nhân viên thực hiện cuộc gọi:
        Lead được ghi nhận thời điểm contacted_at và trạng thái quá hạn SLA được giải phóng.
        """
        lead_id = "LEAD-101"
        self.assertTrue(self.db.calculate_sla_status(self.db.leads[lead_id])["is_overdue"])

        # Thực hiện cuộc gọi
        updated_lead = self.db.record_call(lead_id, notes="Đã gọi điện tư vấn thành công", user_id="usr-01")
        self.assertIsNotNone(updated_lead["contacted_at"])

        # Trạng thái SLA sau khi gọi
        sla_after = self.db.calculate_sla_status(updated_lead)
        self.assertFalse(sla_after["is_overdue"])
        self.assertEqual(sla_after["delay_text"], "Đã liên hệ")


if __name__ == "__main__":
    unittest.main()
