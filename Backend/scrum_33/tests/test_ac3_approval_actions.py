"""
Kiểm thử Tiêu chí 3 (Acceptance Criteria 3) - Ticket SCRUM-33:
"Ba hành động: Duyệt, Từ chối, Trả lại sửa — hai hành động sau bắt buộc nhập ý kiến"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import (
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_CHANGES_REQUESTED,
    ACTION_APPROVE,
    ACTION_REJECT,
    ACTION_REQUEST_CHANGES
)


class TestAC3ApprovalActions(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_action_approve_succeeds_with_or_without_comment(self):
        """
        Hành động 1: DUYỆT (APPROVE)
        - Trạng thái chuyển thành STATUS_APPROVED.
        - Không bắt buộc nhập ý kiến (có thể bỏ trống hoặc có ý kiến).
        """
        # Duyệt không kèm ý kiến
        q_approved_1 = self.db.approve_quote("Q-302", actor_id="usr-03", comment="")
        self.assertEqual(q_approved_1["status"], STATUS_APPROVED)
        self.assertEqual(q_approved_1["approved_by"], "usr-03")

        history = self.db.get_approval_history("Q-302")
        latest = history[-1]
        self.assertEqual(latest["action"], ACTION_APPROVE)
        self.assertTrue(len(latest["comment"]) > 0) # Hệ thống tự gắn lời mặc định nếu trống

    def test_action_reject_requires_mandatory_comment(self):
        """
        Hành động 2: TỪ CHỐI (REJECT)
        - BẮT BUỘC nhập ý kiến/lý do từ chối.
        - Nếu để trống, chỉ nhập khoảng trắng -> Raise ValueError.
        - Khi có ý kiến hợp lệ -> Trạng thái chuyển thành STATUS_REJECTED, can_edit = False.
        """
        # Thử từ chối với ý kiến rỗng
        with self.assertRaises(ValueError) as ctx1:
            self.db.reject_quote("Q-302", actor_id="usr-03", comment="")
        self.assertIn("BẮT BUỘC", str(ctx1.exception))

        # Thử từ chối với toàn dấu cách
        with self.assertRaises(ValueError) as ctx2:
            self.db.reject_quote("Q-302", actor_id="usr-03", comment="     ")
        self.assertIn("BẮT BUỘC", str(ctx2.exception))

        # Từ chối với lý do cụ thể hợp lệ -> Thành công
        reason = "Biên lợi nhuận của hợp đồng này dưới 15%, không đạt chỉ tiêu tài chính quý 4."
        q_rejected = self.db.reject_quote("Q-302", actor_id="usr-03", comment=reason)
        self.assertEqual(q_rejected["status"], STATUS_REJECTED)
        self.assertFalse(q_rejected["can_edit"])

        history = self.db.get_approval_history("Q-302")
        latest = history[-1]
        self.assertEqual(latest["action"], ACTION_REJECT)
        self.assertEqual(latest["comment"], reason)

    def test_action_request_changes_requires_mandatory_comment(self):
        """
        Hành động 3: TRẢ LẠI SỬA (REQUEST_CHANGES)
        - BẮT BUỘC nhập ý kiến/hướng dẫn sửa đổi.
        - Nếu để trống, chỉ nhập khoảng trắng -> Raise ValueError.
        - Khi có ý kiến hợp lệ -> Trạng thái chuyển thành STATUS_CHANGES_REQUESTED, can_edit = True.
        """
        # Thử trả lại sửa với ý kiến rỗng
        with self.assertRaises(ValueError) as ctx1:
            self.db.request_changes_quote("Q-302", actor_id="usr-03", comment="")
        self.assertIn("BẮT BUỘC", str(ctx1.exception))

        # Thử trả lại sửa với chỉ khoảng trắng
        with self.assertRaises(ValueError) as ctx2:
            self.db.request_changes_quote("Q-302", actor_id="usr-03", comment="   \t  \n ")
        self.assertIn("BẮT BUỘC", str(ctx2.exception))

        # Trả lại sửa với hướng dẫn cụ thể -> Thành công
        instruction = "Vui lòng đàm phán lại giảm chiết khấu xuống 10% hoặc đổi sang cam kết thanh toán 100% trước khi triển khai."
        q_changes = self.db.request_changes_quote("Q-302", actor_id="usr-03", comment=instruction)
        self.assertEqual(q_changes["status"], STATUS_CHANGES_REQUESTED)
        self.assertTrue(q_changes["can_edit"]) # NVKD được phép sửa tiếp

        history = self.db.get_approval_history("Q-302")
        latest = history[-1]
        self.assertEqual(latest["action"], ACTION_REQUEST_CHANGES)
        self.assertEqual(latest["comment"], instruction)


if __name__ == "__main__":
    unittest.main()
