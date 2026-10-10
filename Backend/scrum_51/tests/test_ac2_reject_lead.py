"""
Unit Test - Tiêu chí chấp nhận 2 (SCRUM-51):
"Từ chối bắt buộc nhập lý do, lead quay lại hàng chờ phân bổ"
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import (
    STATUS_ASSIGNED,
    STATUS_IN_CARE,
    STATUS_PENDING_ALLOCATION
)
from database import db


class TestRejectLeadCriteria(unittest.TestCase):
    def setUp(self):
        db.reset_demo_data()

    def test_reject_without_reason_is_strictly_rejected(self):
        """
        RÀNG BUỘC CỐT LÕI: Từ chối lead BẮT BUỘC phải nhập lý do.
        Nếu để trống hoặc chỉ nhập khoảng trắng -> Phải chặn và báo lỗi!
        """
        lead = db.create_lead(
            name="Khách Hàng Test Ràng Buộc",
            company="Công ty Gamma",
            phone="0901 111 222",
            email="gamma@test.vn",
            assigned_to_id="usr-01"
        )

        # 1. Thử từ chối với lý do rỗng
        with self.assertRaises(ValueError) as ctx:
            db.reject_lead(lead["id"], user_id="usr-01", reason="")
        self.assertIn("BẮT BUỘC", str(ctx.exception))

        # 2. Thử từ chối với lý do toàn khoảng trắng
        with self.assertRaises(ValueError) as ctx:
            db.reject_lead(lead["id"], user_id="usr-01", reason="   \t  \n  ")
        self.assertIn("BẮT BUỘC", str(ctx.exception))

        # Đảm bảo trạng thái lead không bị thay đổi khi từ chối thất bại
        db_lead = db.get_lead(lead["id"])
        self.assertEqual(db_lead["status"], STATUS_ASSIGNED)
        self.assertEqual(db_lead["assigned_to_id"], "usr-01")

    def test_reject_with_valid_reason_moves_to_pending_allocation_queue(self):
        """
        Khi nhập lý do hợp lệ:
        - Lead chuyển sang trạng thái PENDING_ALLOCATION (Hàng chờ phân bổ).
        - Gỡ nhân viên phụ trách (assigned_to_id = None).
        - Lưu lý do và lịch sử từ chối.
        - Gửi thông báo tới Trưởng nhóm.
        """
        lead = db.create_lead(
            name="Khách Hàng Test Hàng Chờ",
            company="Công ty Delta",
            phone="0902 333 444",
            email="delta@test.vn",
            assigned_to_id="usr-01"
        )

        reason = "Quá tải việc, không thể tiếp nhận thêm lead trong tuần này"
        updated_lead = db.reject_lead(lead["id"], user_id="usr-01", reason=reason)

        # 1. Trạng thái phải là PENDING_ALLOCATION
        self.assertEqual(updated_lead["status"], STATUS_PENDING_ALLOCATION)

        # 2. Nhân viên phụ trách bị gỡ để trưởng nhóm phân bổ lại
        self.assertIsNone(updated_lead["assigned_to_id"])
        self.assertIsNone(updated_lead["assigned_to_name"])

        # 3. Lý do từ chối được lưu chính xác
        self.assertEqual(updated_lead["rejection_reason"], reason)
        self.assertEqual(len(updated_lead["rejection_history"]), 1)
        self.assertEqual(updated_lead["rejection_history"][0]["rejected_by_id"], "usr-01")
        self.assertEqual(updated_lead["rejection_history"][0]["reason"], reason)

        # 4. Kiểm tra thông báo gửi cho Trưởng nhóm
        notifs = db.get_notifications(recipient_id="usr-03")
        reject_notifs = [n for n in notifs if n["lead_id"] == lead["id"]]
        self.assertTrue(len(reject_notifs) > 0)
        self.assertIn("TỪ CHỐI", reject_notifs[0]["title"])
        self.assertIn(reason, reject_notifs[0]["message"])


if __name__ == "__main__":
    unittest.main()
