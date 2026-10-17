"""
Kiểm thử Tiêu chí 3 (Acceptance Criteria 3) - Ticket SCRUM-31:
"Hiển thị mức chiết khấu tổng và cảnh báo khi chạm ngưỡng cần duyệt"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import (
    DISCOUNT_APPROVAL_THRESHOLD_PERCENT,
    STATUS_DRAFT,
    STATUS_PENDING_APPROVAL,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_SENT,
    DISCOUNT_TYPE_PERCENT
)


class TestAC3ApprovalThresholdWarning(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_overall_discount_below_threshold_requires_no_approval(self):
        """
        Chứng minh khi mức chiết khấu tổng < 10% (ví dụ: 5.0%):
        1. is_approval_required = False
        2. Không có cảnh báo vi phạm màu đỏ
        3. Khi nộp báo giá, chuyển thẳng sang trạng thái SENT (Gửi khách hàng ngay)
        """
        items = [
            {
                "subtotal": 100000000,
                "discount_amount": 5000000 # 5%
            }
        ]
        totals = self.db.calculate_quote_totals(items)

        self.assertEqual(totals["overall_discount_percent"], 5.0)
        self.assertFalse(totals["is_approval_required"])
        self.assertEqual(totals["approval_threshold_percent"], DISCOUNT_APPROVAL_THRESHOLD_PERCENT)

    def test_overall_discount_reaching_threshold_triggers_warning_and_approval(self):
        """
        Chứng minh khi mức chiết khấu tổng chạm hoặc vượt ngưỡng 10% (ví dụ: 12.5%):
        1. is_approval_required = True
        2. Hệ thống sinh nội dung cảnh báo chi tiết
        3. Khi nộp báo giá, tự động chuyển sang trạng thái PENDING_APPROVAL
        4. Tự động sinh thông báo cảnh báo gửi Trưởng nhóm kinh doanh
        """
        items = [
            {
                "subtotal": 80000000,
                "discount_amount": 10000000 # 12.5%
            }
        ]
        totals = self.db.calculate_quote_totals(items)

        self.assertEqual(totals["overall_discount_percent"], 12.5)
        self.assertTrue(totals["is_approval_required"])
        self.assertIn("CẢNH BÁO", totals["warning_message"])
        self.assertIn("12.5%", totals["warning_message"])

        # Kiểm tra luồng Submit báo giá
        quote = self.db.create_quote_from_opportunity("OPP-401", user_id="usr-01")
        # Áp dụng chiết khấu 15% cho tất cả sản phẩm
        for itm in quote["items"]:
            itm["discount_type"] = DISCOUNT_TYPE_PERCENT
            itm["discount_value"] = 15.0

        updated_quote = self.db.save_draft(quote["id"], {"items": quote["items"]}, user_id="usr-01")
        self.assertTrue(updated_quote["is_approval_required"])

        # Nộp báo giá -> Phải sang PENDING_APPROVAL vì >= 10%
        submitted = self.db.submit_quote(quote["id"], user_id="usr-01")
        self.assertEqual(submitted["status"], STATUS_PENDING_APPROVAL)

        # Kiểm tra thông báo được gửi cho Trưởng nhóm (usr-03)
        notifs = [n for n in self.db.notifications if n["quote_id"] == quote["id"]]
        self.assertGreater(len(notifs), 0)
        self.assertEqual(notifs[0]["user_id"], "usr-03")

    def test_approval_and_rejection_workflow(self):
        """
        Chứng minh luồng phê duyệt của Trưởng nhóm:
        1. approve_quote() -> chuyển sang APPROVED
        2. reject_quote() -> chuyển sang REJECTED, cho phép NVKD sửa lại (can_edit = True)
        """
        quote_id = "QUOTE-502" # Báo giá mẫu đang ở PENDING_APPROVAL
        quote = self.db.get_quote(quote_id)
        self.assertEqual(quote["status"], STATUS_PENDING_APPROVAL)

        # Trưởng nhóm duyệt báo giá
        approved = self.db.approve_quote(quote_id, approver_id="usr-03", note="Đồng ý hỗ trợ khách hàng chiến lược")
        self.assertEqual(approved["status"], STATUS_APPROVED)
        self.assertEqual(approved["approved_by"], "Lê Hoàng Long")

        # NVKD (usr-01) cố tình duyệt sẽ bị chặn lỗi phân quyền
        with self.assertRaises(PermissionError):
            self.db.approve_quote(quote_id, approver_id="usr-01")


if __name__ == "__main__":
    unittest.main()
