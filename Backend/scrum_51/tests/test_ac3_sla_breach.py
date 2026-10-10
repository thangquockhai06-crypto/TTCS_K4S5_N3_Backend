"""
Unit Test - Tiêu chí chấp nhận 3 (SCRUM-51):
"Quá SLA phản hồi mà chưa liên hệ thì lead được gắn cờ và báo cho trưởng nhóm"
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import (
    STATUS_ASSIGNED,
    STATUS_IN_CARE,
    STATUS_CONTACTED
)
from database import db


class TestSLABreachCriteria(unittest.TestCase):
    def setUp(self):
        db.reset_demo_data()

    def test_overdue_lead_without_contact_is_flagged_and_alerts_team_lead(self):
        """
        Kiểm tra Tiêu chí 3:
        Một lead được phân bổ hoặc đang chăm sóc, nhưng quá hạn SLA phản hồi mà chưa liên hệ:
        - Lead tự động bị gắn cờ is_flagged = True.
        - Có flag_reason cảnh báo.
        - Tự động sinh thông báo khẩn cấp (level='URGENT') gửi cho Trưởng nhóm.
        """
        now = datetime.now()

        # Tạo lead có thời hạn SLA 30 giây
        lead = db.create_lead(
            name="Khách Hàng Quá Hạn Test",
            company="Công ty Epsilon",
            phone="0903 555 666",
            email="epsilon@test.vn",
            assigned_to_id="usr-01",
            sla_seconds=30
        )
        self.assertFalse(lead["is_flagged"])

        # Giả lập thời gian trôi qua 35 giây (vượt quá hạn SLA 30s)
        future_time = now + timedelta(seconds=35)

        # Quét kiểm tra SLA tại mốc thời gian future_time
        flagged_leads = db.check_and_flag_sla_breaches(reference_time=future_time)

        # 1. Lead phải nằm trong danh sách bị gắn cờ
        flagged_ids = [l["id"] for l in flagged_leads]
        self.assertIn(lead["id"], flagged_ids)

        # 2. Kiểm tra trong DB
        db_lead = db.get_lead(lead["id"])
        self.assertTrue(db_lead["is_flagged"])
        self.assertIsNotNone(db_lead["flagged_at"])
        self.assertIn("Quá SLA", db_lead["flag_reason"])

        # 3. Kiểm tra thông báo gửi cho Trưởng nhóm Lê Hoàng Nam (usr-03)
        notifs = db.get_notifications(recipient_id="usr-03")
        urgent_notifs = [n for n in notifs if n["lead_id"] == lead["id"] and n["level"] == "URGENT"]
        self.assertTrue(len(urgent_notifs) > 0)
        self.assertIn("QUÁ HẠN SLA", urgent_notifs[0]["title"])
        self.assertIn(lead["name"], urgent_notifs[0]["message"])

    def test_contacted_lead_is_never_flagged(self):
        """
        Nếu nhân viên đã liên hệ khách hàng thành công (contacted_at is not None):
        Dù thời gian có trôi qua bao lâu thì lead cũng KHÔNG bị gắn cờ vi phạm SLA!
        """
        lead = db.create_lead(
            name="Khách Hàng Đã Liên Hệ Test",
            company="Công ty Zeta",
            phone="0904 777 888",
            email="zeta@test.vn",
            assigned_to_id="usr-01",
            sla_seconds=30
        )

        # Nhân viên nhận lead và thực hiện liên hệ
        db.accept_lead(lead["id"], user_id="usr-01")
        db.log_contact(lead["id"], user_id="usr-01", channel="Điện thoại", notes="Đã gọi điện tư vấn thành công")

        # Giả lập trôi qua 10 ngày sau
        future_time = datetime.now() + timedelta(days=10)
        db.check_and_flag_sla_breaches(reference_time=future_time)

        # Lead vẫn không bị gắn cờ
        db_lead = db.get_lead(lead["id"])
        self.assertFalse(db_lead["is_flagged"])
        self.assertEqual(db_lead["status"], STATUS_CONTACTED)

    def test_fast_forward_simulation(self):
        """Kiểm tra tính năng tua nhanh SLA trong simulator"""
        lead = db.create_lead(
            name="Lead Simulator Test",
            company="Công ty Eta",
            phone="0905 888 999",
            email="eta@test.vn",
            assigned_to_id="usr-01",
            sla_seconds=120
        )
        self.assertFalse(lead["is_flagged"])

        # Tua nhanh 200 giây
        updated = db.fast_forward_lead_sla(lead["id"], forward_seconds=200)
        self.assertTrue(updated["is_flagged"])


if __name__ == "__main__":
    unittest.main()
