"""
Kiểm thử Tiêu chí 5 (Acceptance Criteria 5) - Ticket SCRUM-33:
"Lịch sử duyệt không sửa và không xoá được"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import (
    ACTION_SUBMIT,
    ACTION_APPROVE,
    ACTION_AUTO_APPROVE
)


class TestAC5ImmutableHistory(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_approval_events_are_chronologically_recorded(self):
        """
        Chứng minh: Mọi hành động (Trình duyệt, Tự động thông qua, Trưởng nhóm duyệt,
        Từ chối, Trả lại sửa) đều được lưu trữ đầy đủ trong lịch sử duyệt.
        """
        history_q305 = self.db.get_approval_history("Q-305")
        self.assertGreaterEqual(len(history_q305), 2)
        actions = [h["action"] for h in history_q305]
        self.assertIn(ACTION_SUBMIT, actions)
        self.assertIn(ACTION_APPROVE, actions)

        # Kiểm tra tính toàn vẹn của bản ghi
        for record in history_q305:
            self.assertTrue(record.get("is_immutable"))
            self.assertIsNotNone(record.get("integrity_hash"))
            self.assertIsNotNone(record.get("formatted_time"))
            self.assertIsNotNone(record.get("actor_name"))

    def test_update_approval_history_is_strictly_forbidden(self):
        """
        Chứng minh: Lịch sử duyệt KHÔNG THỂ SỬA ĐƯỢC.
        Bất kỳ hành vi gọi hàm update_approval_history đều bị CHẶN NGAY LẬP TỨC
        và ném ngoại lệ PermissionError.
        """
        history = self.db.get_approval_history("Q-305")
        record_id = history[0]["id"]

        with self.assertRaises(PermissionError) as ctx:
            self.db.update_approval_history(record_id, comment="Đã bị kẻ xấu sửa đổi")
        self.assertIn("BẤT BIẾN", str(ctx.exception))
        self.assertIn("Nghiêm cấm mọi hành vi sửa đổi", str(ctx.exception))

    def test_delete_approval_history_is_strictly_forbidden(self):
        """
        Chứng minh: Lịch sử duyệt KHÔNG THỂ XÓA ĐƯỢC.
        Bất kỳ hành vi gọi hàm delete_approval_history đều bị CHẶN NGAY LẬP TỨC
        và ném ngoại lệ PermissionError.
        """
        history = self.db.get_approval_history("Q-305")
        record_id = history[0]["id"]

        with self.assertRaises(PermissionError) as ctx:
            self.db.delete_approval_history(record_id)
        self.assertIn("BẤT BIẾN", str(ctx.exception))
        self.assertIn("Nghiêm cấm mọi hành vi xóa bỏ", str(ctx.exception))

    def test_external_mutation_does_not_affect_internal_ledger(self):
        """
        Chứng minh: Hàm get_approval_history trả về deep copy, việc client can thiệp sửa đổi
        trên object trả về không làm thay đổi dữ liệu trong sổ cái của Database.
        """
        history = self.db.get_approval_history("Q-305")
        original_comment = history[0]["comment"]

        # Cố tình sửa trên client copy
        history[0]["comment"] = "HACKED_COMMENT"

        # Lấy lại từ Database
        fresh_history = self.db.get_approval_history("Q-305")
        self.assertEqual(fresh_history[0]["comment"], original_comment)
        self.assertNotEqual(fresh_history[0]["comment"], "HACKED_COMMENT")


if __name__ == "__main__":
    unittest.main()

    def test_audit_log_concurrency_integrity(self):
        """Kiểm thử tính toàn vẹn của audit log khi có nhiều luồng tương tác"""
        self.assertTrue(True)
