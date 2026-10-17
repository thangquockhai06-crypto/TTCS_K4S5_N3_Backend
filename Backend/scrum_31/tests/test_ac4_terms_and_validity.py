"""
Kiểm thử Tiêu chí 4 (Acceptance Criteria 4) - Ticket SCRUM-31:
"Khai báo hiệu lực báo giá, điều khoản thanh toán và điều khoản giao hàng"
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database, get_current_time


class TestAC4TermsAndValidity(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_declare_and_update_validity_and_terms(self):
        """
        Chứng minh các trường hiệu lực báo giá, điều khoản thanh toán,
        và điều khoản giao hàng được khai báo và lưu trữ toàn vẹn.
        """
        quote = self.db.create_quote_from_opportunity("OPP-401", user_id="usr-01")

        # Khai báo các điều khoản cụ thể
        custom_form = {
            "title": "Báo giá giải pháp CRM Dược phẩm An Bình",
            "validity_days": 30,
            "payment_terms": "Tạm ứng 40% khi ký hợp đồng, 60% thanh toán sau khi nghiệm thu 15 ngày.",
            "delivery_terms": "Triển khai lắp đặt tại trụ sở khách hàng trong 05 ngày làm việc.",
            "notes": "Cam kết giá cố định trong suốt thời gian hiệu lực 30 ngày.",
            "items": quote["items"]
        }

        updated = self.db.save_draft(quote["id"], custom_form, user_id="usr-01")

        # Kiểm tra tính toàn vẹn
        self.assertEqual(updated["validity_days"], 30)
        self.assertEqual(updated["payment_terms"], custom_form["payment_terms"])
        self.assertEqual(updated["delivery_terms"], custom_form["delivery_terms"])
        self.assertEqual(updated["notes"], custom_form["notes"])

        # Kiểm tra ngày hết hạn hiệu lực
        expected_expiry = (get_current_time() + timedelta(days=30)).strftime("%d/%m/%Y")
        self.assertEqual(updated["valid_until"], expected_expiry)


if __name__ == "__main__":
    unittest.main()
