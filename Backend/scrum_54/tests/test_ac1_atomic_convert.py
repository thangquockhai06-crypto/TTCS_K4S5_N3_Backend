"""
Kiểm thử Tiêu chí 1 (Acceptance Criteria 1) - Ticket SCRUM-54:
"Một thao tác sinh đồng thời khách hàng doanh nghiệp, người liên hệ và cơ hội bán hàng"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database, STATUS_QUALIFIED, STATUS_CONVERTED


class TestAC1AtomicConvert(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_single_operation_generates_three_entities_simultaneously(self):
        """
        Chứng minh chỉ bằng 1 thao tác convert_lead(), hệ thống đồng thời
        sinh ra chính xác 3 thực thể:
        1. Khách hàng doanh nghiệp (Account)
        2. Người liên hệ (Contact)
        3. Cơ hội bán hàng (Opportunity)
        và liên kết chặt chẽ với nhau.
        """
        lead_id = "LEAD-101"
        lead_before = self.db.get_lead(lead_id)
        self.assertIsNotNone(lead_before)
        self.assertEqual(lead_before["status"], STATUS_QUALIFIED)

        # Đếm số lượng thực thể trước khi chuyển đổi
        acc_count_before = len(self.db.accounts)
        con_count_before = len(self.db.contacts)
        opp_count_before = len(self.db.opportunities)

        # 🎯 1 THAO TÁC DUY NHẤT: convert_lead()
        result = self.db.convert_lead(lead_id, user_id="usr-01")

        # 1. Kiểm tra kết quả trả về đầy đủ 3 thực thể
        self.assertIn("account", result)
        self.assertIn("contact", result)
        self.assertIn("opportunity", result)
        self.assertIn("lead", result)

        account = result["account"]
        contact = result["contact"]
        opportunity = result["opportunity"]
        lead_after = result["lead"]

        # 2. Kiểm tra số lượng trong cơ sở dữ liệu đều tăng đúng 1
        self.assertEqual(len(self.db.accounts), acc_count_before + 1)
        self.assertEqual(len(self.db.contacts), con_count_before + 1)
        self.assertEqual(len(self.db.opportunities), opp_count_before + 1)

        # 3. Kiểm tra định danh ID và tồn tại trong DB
        self.assertTrue(account["id"].startswith("ACC-"))
        self.assertTrue(contact["id"].startswith("CON-"))
        self.assertTrue(opportunity["id"].startswith("OPP-"))

        self.assertIn(account["id"], self.db.accounts)
        self.assertIn(contact["id"], self.db.contacts)
        self.assertIn(opportunity["id"], self.db.opportunities)

        # 4. Kiểm tra sự liên kết mật thiết giữa 3 thực thể:
        # - Contact liên kết với Account
        self.assertEqual(contact["account_id"], account["id"])
        # - Opportunity liên kết với cả Account và Contact
        self.assertEqual(opportunity["account_id"], account["id"])
        self.assertEqual(opportunity["contact_id"], contact["id"])

        # - Cả 3 đều lưu vết sinh từ lead gốc
        self.assertEqual(account["created_from_lead_id"], lead_id)
        self.assertEqual(contact["created_from_lead_id"], lead_id)
        self.assertEqual(opportunity["created_from_lead_id"], lead_id)

        # - Lead cũng lưu tham chiếu ngược tới cả 3 thực thể
        self.assertEqual(lead_after["converted_account_id"], account["id"])
        self.assertEqual(lead_after["converted_contact_id"], contact["id"])
        self.assertEqual(lead_after["converted_opportunity_id"], opportunity["id"])


if __name__ == "__main__":
    unittest.main()
