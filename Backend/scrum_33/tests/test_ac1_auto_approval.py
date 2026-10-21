"""
Kiểm thử Tiêu chí 1 (Acceptance Criteria 1) - Ticket SCRUM-33:
"Chiết khấu dưới ngưỡng thứ nhất thì tự động thông qua, không cần duyệt"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import (
    THRESHOLD_1_PERCENT,
    STATUS_APPROVED,
    STATUS_DRAFT,
    ACTION_AUTO_APPROVE,
    AUTHORITY_AUTO,
    ROLE_SYSTEM
)


class TestAC1AutoApproval(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_quote_below_threshold_1_automatically_approved(self):
        """
        Chứng minh:
        - Báo giá có mức chiết khấu dưới ngưỡng 1 (< 10.0%) và không dưới giá sàn:
          -> Tự động thông qua ngay khi trình duyệt (status = APPROVED)
          -> Không cần đưa vào hàng chờ duyệt của Trưởng nhóm
          -> Ghi nhận hành động AUTO_APPROVE trong lịch sử duyệt
        """
        # Tạo báo giá mới với chiết khấu 5% (< 10%)
        quote_data = {
            "title": "Báo giá phần mềm CRM - Chiết khấu 5%",
            "account_name": "Công ty TNHH ABC",
            "items": [
                {
                    "product_id": "PRD-001", # CRM Enterprise 24M, sàn 18M
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 5.0 # Sau chiết khấu: 22.8M > sàn 18M
                }
            ]
        }
        quote = self.db.create_quote(quote_data, user_id="usr-01")
        self.assertEqual(quote["status"], STATUS_DRAFT)
        self.assertEqual(quote["discount_rate"], 5.0)
        self.assertLess(quote["discount_rate"], THRESHOLD_1_PERCENT)
        self.assertFalse(quote["below_floor_price"])
        self.assertEqual(quote["approval_authority"], AUTHORITY_AUTO)

        # 🎯 THAO TÁC: NVKD Trình duyệt báo giá
        submitted_quote = self.db.submit_quote_for_approval(quote["id"], user_id="usr-01")

        # 🎯 KẾT QUẢ MONG ĐỢI: Tự động thông qua (APPROVED) ngay lập tức!
        self.assertEqual(submitted_quote["status"], STATUS_APPROVED)
        self.assertIsNotNone(submitted_quote["approved_at"])
        self.assertEqual(submitted_quote["approved_by"], "usr-sys")

        # Kiểm tra lịch sử duyệt có sự kiện AUTO_APPROVE của Hệ thống
        history = self.db.get_approval_history(quote["id"])
        auto_events = [h for h in history if h["action"] == ACTION_AUTO_APPROVE]
        self.assertEqual(len(auto_events), 1)
        self.assertEqual(auto_events[0]["actor_role"], ROLE_SYSTEM)
        self.assertIn("TỰ ĐỘNG THÔNG QUA", auto_events[0]["comment"])

    def test_seed_quote_q301_is_already_auto_approved(self):
        """
        Kiểm tra dữ liệu mẫu Q-301 đã được hệ thống tự động thông qua chuẩn nghiệp vụ.
        """
        q = self.db.get_quote("Q-301")
        self.assertIsNotNone(q)
        self.assertEqual(q["status"], STATUS_APPROVED)
        self.assertLess(q["discount_rate"], THRESHOLD_1_PERCENT)
        self.assertFalse(q["below_floor_price"])
        self.assertEqual(q["approved_by"], "usr-sys")


if __name__ == "__main__":
    unittest.main()
