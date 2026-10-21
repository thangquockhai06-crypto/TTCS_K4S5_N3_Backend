"""
Kiểm thử Tiêu chí 2 (Acceptance Criteria 2) - Ticket SCRUM-33:
"Vượt ngưỡng thứ nhất do Trưởng nhóm duyệt; vượt ngưỡng thứ hai hoặc dưới giá sàn thì bắt buộc Giám đốc kinh doanh duyệt"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import (
    THRESHOLD_1_PERCENT,
    THRESHOLD_2_PERCENT,
    STATUS_PENDING_APPROVAL,
    STATUS_APPROVED,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR,
    ROLE_SALES_REP,
    AUTHORITY_TEAM_LEAD,
    AUTHORITY_DIRECTOR
)


class TestAC2ApprovalHierarchy(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_quote_exceeding_threshold_1_requires_team_lead(self):
        """
        Chứng minh: Chiết khấu từ 10% đến 20% (vượt ngưỡng 1) và không dưới giá sàn:
        -> Yêu cầu Trưởng nhóm kinh doanh duyệt (required_role = ROLE_TEAM_LEAD)
        -> Trưởng nhóm duyệt thành công
        """
        quote_data = {
            "title": "Báo giá chiết khấu 15%",
            "account_name": "Công ty Khách hàng B2B",
            "items": [
                {
                    "product_id": "PRD-001", # 24M, sàn 18M
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 15.0 # Sau giảm 20.4M > sàn 18M
                }
            ]
        }
        quote = self.db.create_quote(quote_data, user_id="usr-01")
        self.assertEqual(quote["discount_rate"], 15.0)
        self.assertEqual(quote["approval_authority"], AUTHORITY_TEAM_LEAD)
        self.assertEqual(quote["required_role"], ROLE_TEAM_LEAD)

        submitted = self.db.submit_quote_for_approval(quote["id"], user_id="usr-01")
        self.assertEqual(submitted["status"], STATUS_PENDING_APPROVAL)
        self.assertEqual(submitted["required_role"], ROLE_TEAM_LEAD)

        # Trưởng nhóm duyệt hợp lệ
        approved = self.db.approve_quote(quote["id"], actor_id="usr-03", comment="Trưởng nhóm duyệt mức 15%")
        self.assertEqual(approved["status"], STATUS_APPROVED)
        self.assertEqual(approved["approved_by"], "usr-03")

    def test_quote_exceeding_threshold_2_requires_director(self):
        """
        Chứng minh: Chiết khấu > 20% (vượt ngưỡng 2):
        -> Bắt buộc Giám đốc kinh doanh duyệt (required_role = ROLE_DIRECTOR)
        -> Trưởng nhóm cố tình duyệt sẽ bị CHẶN NGAY (PermissionError)
        -> Giám đốc duyệt thì thành công
        """
        quote_data = {
            "title": "Báo giá chiết khấu sâu 25%",
            "account_name": "Tập đoàn Lớn",
            "items": [
                {
                    "product_id": "PRD-001",
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 25.0 # 24M -> 18M (bằng sàn)
                }
            ]
        }
        quote = self.db.create_quote(quote_data, user_id="usr-01")
        self.assertEqual(quote["discount_rate"], 25.0)
        self.assertGreater(quote["discount_rate"], THRESHOLD_2_PERCENT)
        self.assertEqual(quote["approval_authority"], AUTHORITY_DIRECTOR)
        self.assertEqual(quote["required_role"], ROLE_DIRECTOR)

        submitted = self.db.submit_quote_for_approval(quote["id"], user_id="usr-01")
        self.assertEqual(submitted["status"], STATUS_PENDING_APPROVAL)

        # 🚨 KIỂM TRA BẢO MẬT: Trưởng nhóm (usr-03) cố tình duyệt -> PHẢI BỊ CHẶN!
        with self.assertRaises(PermissionError) as ctx:
            self.db.approve_quote(quote["id"], actor_id="usr-03", comment="Trưởng nhóm duyệt vượt quyền")
        self.assertIn("GIÁM ĐỐC KINH DOANH", str(ctx.exception))

        # 👑 Giám đốc (usr-04) duyệt -> THÀNH CÔNG!
        approved = self.db.approve_quote(quote["id"], actor_id="usr-04", comment="Giám đốc đồng ý chiết khấu 25%")
        self.assertEqual(approved["status"], STATUS_APPROVED)
        self.assertEqual(approved["approved_by"], "usr-04")

    def test_quote_below_floor_price_requires_director_even_if_discount_is_low(self):
        """
        Chứng minh: Dù chiết khấu chỉ 5% (< ngưỡng 1 = 10%), nhưng nếu đơn giá sau chiết khấu
        thấp hơn GIÁ SÀN (Floor price):
        -> Bắt buộc Giám đốc kinh doanh duyệt!
        -> Không được tự động thông qua!
        -> Trưởng nhóm không có quyền duyệt!
        """
        quote_data = {
            "title": "Báo giá phá giá sàn",
            "account_name": "Khách ép giá",
            "items": [
                {
                    "product_id": "PRD-001", # Giá sàn 18.000.000 đ
                    "quantity": 1,
                    "unit_price": 17000000, # Đơn giá bán khởi điểm thấp hơn sàn 18M
                    "discount_percent": 5.0 # Chiết khấu chỉ 5%
                }
            ]
        }
        quote = self.db.create_quote(quote_data, user_id="usr-01")
        self.assertTrue(quote["below_floor_price"])
        self.assertEqual(quote["approval_authority"], AUTHORITY_DIRECTOR)
        self.assertEqual(quote["required_role"], ROLE_DIRECTOR)

        submitted = self.db.submit_quote_for_approval(quote["id"], user_id="usr-01")
        self.assertEqual(submitted["status"], STATUS_PENDING_APPROVAL)

        # Trưởng nhóm duyệt -> BỊ CHẶN!
        with self.assertRaises(PermissionError):
            self.db.approve_quote(quote["id"], actor_id="usr-03")

        # Giám đốc duyệt -> THÀNH CÔNG
        approved = self.db.approve_quote(quote["id"], actor_id="usr-04", comment="Giám đốc duyệt ngoại lệ dưới giá sàn")
        self.assertEqual(approved["status"], STATUS_APPROVED)

    def test_sales_rep_cannot_approve_quotes(self):
        """
        Chứng minh: Nhân viên kinh doanh (Sales Rep) hoàn toàn không có quyền duyệt báo giá.
        """
        q = self.db.get_quote("Q-302") # Đang chờ duyệt
        with self.assertRaises(PermissionError):
            self.db.approve_quote(q["id"], actor_id="usr-01", comment="NVKD tự duyệt")


if __name__ == "__main__":
    unittest.main()
