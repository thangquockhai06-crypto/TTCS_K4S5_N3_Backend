"""
Kiểm thử Tiêu chí 5 (Acceptance Criteria 5) - Ticket SCRUM-31:
"Lưu nháp và sửa tiếp được"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import STATUS_DRAFT, STATUS_SENT


class TestAC5SaveDraftAndEdit(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_save_draft_preserves_editable_state_and_increments_version(self):
        """
        Chứng minh:
        1. Báo giá khi lưu nháp có trạng thái STATUS_DRAFT
        2. Cờ can_edit = True cho phép sửa tiếp không giới hạn
        3. Mỗi lần lưu nháp tiếp theo, phiên bản nháp draft_version tự động tăng (v1 -> v2 -> v3)
        4. Cho phép sửa lại sản phẩm, chiết khấu, điều khoản ở mọi lần lưu
        """
        # 1. Tạo mới -> Ban đầu là bản nháp v1
        quote = self.db.create_quote_from_opportunity("OPP-401", user_id="usr-01")
        self.assertEqual(quote["status"], STATUS_DRAFT)
        self.assertTrue(quote["can_edit"])
        self.assertEqual(quote["draft_version"], 1)

        # 2. Lần lưu nháp thứ 2 (v2): Thêm ghi chú
        v2 = self.db.save_draft(
            quote["id"],
            {
                "title": quote["title"] + " (Cập nhật lần 1)",
                "items": quote["items"],
                "notes": "Đang đợi khách xác nhận số lượng chi tiết vào buổi chiều."
            },
            user_id="usr-01"
        )
        self.assertEqual(v2["status"], STATUS_DRAFT)
        self.assertTrue(v2["can_edit"])
        self.assertEqual(v2["draft_version"], 2)
        self.assertIn("(Cập nhật lần 1)", v2["title"])

        # 3. Lần lưu nháp thứ 3 (v3): Sửa số lượng sản phẩm
        items_v3 = list(v2["items"])
        items_v3[0]["quantity"] = 5
        v3 = self.db.save_draft(
            quote["id"],
            {
                "items": items_v3,
                "notes": "Khách vừa gọi chốt tăng số lượng lên 5."
            },
            user_id="usr-01"
        )
        self.assertEqual(v3["status"], STATUS_DRAFT)
        self.assertTrue(v3["can_edit"])
        self.assertEqual(v3["draft_version"], 3)
        self.assertEqual(v3["items"][0]["quantity"], 5)

    def test_submitted_quote_cannot_be_arbitrarily_edited_unless_rejected(self):
        """
        Chứng minh báo giá khi đã nộp/gửi chính thức (không còn là nháp)
        sẽ không được tùy tiện sửa đổi, bảo đảm tính pháp lý của chứng từ.
        """
        quote = self.db.create_quote_from_opportunity("OPP-401", user_id="usr-01")
        # Nộp báo giá (chiết khấu 0% nên sang SENT)
        submitted = self.db.submit_quote(quote["id"], user_id="usr-01")
        self.assertEqual(submitted["status"], STATUS_SENT)
        self.assertFalse(submitted["can_edit"])

        # Cố tình gọi save_draft trên báo giá đã gửi sẽ bị chặn
        with self.assertRaises(PermissionError):
            self.db.save_draft(quote["id"], {"items": quote["items"]}, user_id="usr-01")


if __name__ == "__main__":
    unittest.main()
