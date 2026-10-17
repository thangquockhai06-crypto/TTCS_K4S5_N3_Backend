"""
Kiểm thử Tiêu chí 4 (Acceptance Criteria 4) - Ticket SCRUM-33:
"Chỉ báo giá đã duyệt mới gửi được cho khách"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import (
    STATUS_APPROVED,
    STATUS_SENT,
    STATUS_DRAFT,
    STATUS_PENDING_APPROVAL,
    STATUS_CHANGES_REQUESTED,
    STATUS_REJECTED
)


class TestAC4SendToCustomer(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_approved_quote_can_be_sent_to_customer(self):
        """
        Chứng minh: Báo giá ở trạng thái STATUS_APPROVED:
        -> Gửi thành công cho khách hàng
        -> Trạng thái chuyển thành STATUS_SENT
        -> Ghi nhận thời gian gửi và người gửi
        """
        # Q-301 là báo giá đã được duyệt (APPROVED)
        q = self.db.get_quote("Q-301")
        self.assertEqual(q["status"], STATUS_APPROVED)

        # 🎯 THAO TÁC: Gửi báo giá cho khách
        sent_quote = self.db.send_to_customer("Q-301", actor_id="usr-01")

        # 🎯 KẾT QUẢ MONG ĐỢI: Trạng thái chuyển sang SENT
        self.assertEqual(sent_quote["status"], STATUS_SENT)
        self.assertIsNotNone(sent_quote["sent_at"])
        self.assertEqual(sent_quote["sent_by"], "usr-01")

    def test_unapproved_quotes_cannot_be_sent_to_customer(self):
        """
        Chứng minh: Bất kỳ báo giá nào chưa được phê duyệt (DRAFT, PENDING_APPROVAL,
        CHANGES_REQUESTED, REJECTED):
        -> BỊ CHẶN TUYỆT ĐỐI khi cố gửi cho khách
        -> Ném ngoại lệ ValueError với thông báo nghiệp vụ rõ ràng
        """
        # 1. Báo giá đang chờ duyệt (PENDING_APPROVAL - Q-302)
        q_pending = self.db.get_quote("Q-302")
        self.assertEqual(q_pending["status"], STATUS_PENDING_APPROVAL)
        with self.assertRaises(ValueError) as ctx1:
            self.db.send_to_customer("Q-302", actor_id="usr-01")
        self.assertIn("CHỈ BÁO GIÁ ĐÃ PHÊ DUYỆT", str(ctx1.exception))
        self.assertEqual(self.db.get_quote("Q-302")["status"], STATUS_PENDING_APPROVAL)

        # 2. Báo giá đang bị trả lại sửa (CHANGES_REQUESTED - Q-306)
        q_changes = self.db.get_quote("Q-306")
        self.assertEqual(q_changes["status"], STATUS_CHANGES_REQUESTED)
        with self.assertRaises(ValueError) as ctx2:
            self.db.send_to_customer("Q-306", actor_id="usr-01")
        self.assertIn("CHỈ BÁO GIÁ ĐÃ PHÊ DUYỆT", str(ctx2.exception))

        # 3. Báo giá bị từ chối duyệt (REJECTED - Q-307)
        q_rejected = self.db.get_quote("Q-307")
        self.assertEqual(q_rejected["status"], STATUS_REJECTED)
        with self.assertRaises(ValueError) as ctx3:
            self.db.send_to_customer("Q-307", actor_id="usr-01")
        self.assertIn("CHỈ BÁO GIÁ ĐÃ PHÊ DUYỆT", str(ctx3.exception))

        # 4. Báo giá bản nháp (DRAFT)
        draft = self.db.create_quote({"title": "Bản nháp thử nghiệm", "items": []}, user_id="usr-01")
        self.assertEqual(draft["status"], STATUS_DRAFT)
        with self.assertRaises(ValueError) as ctx4:
            self.db.send_to_customer(draft["id"], actor_id="usr-01")
        self.assertIn("CHỈ BÁO GIÁ ĐÃ PHÊ DUYỆT", str(ctx4.exception))


if __name__ == "__main__":
    unittest.main()
