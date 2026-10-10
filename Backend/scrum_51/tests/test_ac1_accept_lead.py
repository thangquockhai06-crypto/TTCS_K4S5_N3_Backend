"""
Unit Test - Tiêu chí chấp nhận 1 (SCRUM-51):
"Nhân viên nhận lead thì lead chuyển sang Đang chăm sóc"
"""

import unittest
import sys
import os

# Thêm đường dẫn thư mục gốc dự án
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import (
    STATUS_ASSIGNED,
    STATUS_IN_CARE
)
from database import db


class TestAcceptLeadCriteria(unittest.TestCase):
    def setUp(self):
        db.reset_demo_data()

    def test_accept_lead_transitions_to_in_care(self):
        """
        Kiểm tra khi nhân viên bấm nhận lead:
        Trạng thái của lead phải chuyển sang 'IN_CARE' (Đang chăm sóc).
        """
        # Tạo lead mới đang ở trạng thái chờ tiếp nhận (ASSIGNED)
        lead = db.create_lead(
            name="Khách Hàng Test 1",
            company="Công ty Alpha",
            phone="0911 222 333",
            email="alpha@test.vn",
            assigned_to_id="usr-01",
            sla_seconds=120
        )
        self.assertEqual(lead["status"], STATUS_ASSIGNED)
        self.assertIsNone(lead["accepted_at"])

        # Nhân viên usr-01 bấm nhận lead
        updated_lead = db.accept_lead(lead["id"], user_id="usr-01")

        # 1. Trạng thái phải là IN_CARE (Đang chăm sóc)
        self.assertEqual(updated_lead["status"], STATUS_IN_CARE)

        # 2. Thời điểm accepted_at phải được ghi nhận
        self.assertIsNotNone(updated_lead["accepted_at"])

        # 3. Người phụ trách phải là usr-01
        self.assertEqual(updated_lead["assigned_to_id"], "usr-01")

        # 4. Kiểm tra dữ liệu lưu trong DB cũng đồng bộ
        db_lead = db.get_lead(lead["id"])
        self.assertEqual(db_lead["status"], STATUS_IN_CARE)
        self.assertIsNotNone(db_lead["accepted_at"])

    def test_accept_non_existent_lead_raises_error(self):
        """Bấm nhận lead không tồn tại phải ném ra ngoại lệ ValueError"""
        with self.assertRaises(ValueError):
            db.accept_lead("LEAD-NON-EXISTENT", user_id="usr-01")

    def test_accept_lead_creates_audit_log(self):
        """Bấm nhận lead phải sinh ra log kiểm toán rõ ràng"""
        lead = db.create_lead(
            name="Khách Hàng Audit Log",
            company="Công ty Beta",
            phone="0988 777 666",
            email="beta@test.vn",
            assigned_to_id="usr-01"
        )
        db.accept_lead(lead["id"], user_id="usr-01")

        logs = db.get_audit_logs(limit=5)
        accepted_logs = [l for l in logs if l["event_type"] == "LEAD_ACCEPTED" and l["lead_id"] == lead["id"]]
        self.assertTrue(len(accepted_logs) > 0)
        self.assertIn("Đang chăm sóc", accepted_logs[0]["details"])


if __name__ == "__main__":
    unittest.main()
