"""
Unit Test - Tiêu chí chấp nhận 3 (AC3):
"Cơ hội tương ứng tự động chuyển sang Đóng thắng với giá trị đúng bằng giá trị hợp đồng"
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import OPP_STAGE_NEGOTIATION, OPP_STAGE_CLOSED_WON


class TestAC3OpportunityClosedWonSync(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.db.reset_to_seed()

    def test_opportunity_automatically_transitions_to_closed_won_with_exact_value(self):
        """
        Kiểm tra:
        - Trước khi lập hợp đồng: Cơ hội OPP-2026-101 ở trạng thái NEGOTIATION, giá trị dự kiến 80.000.000 đ
        - Báo giá BG-2026-001 có giá trị chốt cuối cùng là 83.710.000 đ
        - Sau khi Kế toán lập hợp đồng:
          1. Cơ hội OPP-2026-101 tự động chuyển sang stage CLOSED_WON (Đóng thắng)
          2. Giá trị cơ hội được cập nhật CHÍNH XÁC đúng bằng giá trị hợp đồng (83.710.000 đ)
          3. Ngày thắng (win_date) và mã hợp đồng liên kết (contract_id) được đồng bộ
        """
        # Kiểm tra trạng thái ban đầu của Cơ hội
        opp_before = self.db.get_opportunity("OPP-2026-101")
        self.assertEqual(opp_before["stage"], OPP_STAGE_NEGOTIATION)
        self.assertEqual(opp_before["value"], 80000000)
        self.assertIsNone(opp_before["contract_id"])

        quote = self.db.get_quote("BG-2026-001")
        self.assertEqual(quote["grand_total"], 83710000)

        # Kế toán chuyển báo giá thành hợp đồng
        payload = {
            "contract_number": "HD-2026/010",
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Thanh toán 100% trong vòng 7 ngày làm việc sau khi ký"
        }
        contract = self.db.convert_quote_to_contract("BG-2026-001", payload, "Kế toán viên Mai")

        # Kiểm tra Cơ hội sau khi chuyển đổi
        opp_after = self.db.get_opportunity("OPP-2026-101")

        # 1. Cơ hội tự động chuyển sang CLOSED_WON
        self.assertEqual(opp_after["stage"], OPP_STAGE_CLOSED_WON)

        # 2. Giá trị Cơ hội đúng bằng giá trị Hợp đồng (83.710.000 đ, không phải 80.000.000 đ cũ)
        self.assertEqual(opp_after["value"], contract["grand_total"])
        self.assertEqual(opp_after["value"], 83710000)

        # 3. Đồng bộ mã hợp đồng và ngày ký
        self.assertEqual(opp_after["contract_id"], contract["contract_id"])
        self.assertEqual(opp_after["win_date"], "2026-10-17")

    def test_second_opportunity_also_syncs_correctly(self):
        """Kiểm tra: Thử nghiệm với báo giá thứ 2 (BG-2026-002) gắn cơ hội OPP-2026-102"""
        opp_before = self.db.get_opportunity("OPP-2026-102")
        self.assertEqual(opp_before["stage"], OPP_STAGE_NEGOTIATION)

        payload = {
            "contract_number": "HD-2026/020",
            "signed_date": "2026-10-18",
            "effective_date": "2026-10-18",
            "expiration_date": "2027-10-17",
            "payment_terms": "Net 30"
        }
        contract = self.db.convert_quote_to_contract("BG-2026-002", payload, "Kế toán viên Mai")

        opp_after = self.db.get_opportunity("OPP-2026-102")
        self.assertEqual(opp_after["stage"], OPP_STAGE_CLOSED_WON)
        self.assertEqual(opp_after["value"], contract["grand_total"])
        self.assertEqual(opp_after["value"], 52470000)


if __name__ == "__main__":
    unittest.main()
