"""
Kiểm thử Tiêu chí 2 (Acceptance Criteria 2) - Ticket SCRUM-31:
"Mỗi dòng nhập chiết khấu theo phần trăm hoặc số tiền, hệ thống tính lại thành tiền ngay"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import DISCOUNT_TYPE_PERCENT, DISCOUNT_TYPE_AMOUNT


class TestAC2LineDiscountCalculation(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_percentage_discount_calculation(self):
        """
        Chứng minh chiết khấu theo phần trăm (%):
        Số lượng: 2, Đơn giá: 10.000.000 đ => Thành tiền gốc = 20.000.000 đ
        Chiết khấu: 10%
        => Tiền chiết khấu dòng = 2.000.000 đ
        => Thành tiền sau chiết khấu = 18.000.000 đ
        """
        item = {
            "quantity": 2,
            "unit_price": 10000000,
            "discount_type": DISCOUNT_TYPE_PERCENT,
            "discount_value": 10.0
        }

        result = self.db.calculate_line_item(item)

        self.assertEqual(result["subtotal"], 20000000.0)
        self.assertEqual(result["discount_amount"], 2000000.0)
        self.assertEqual(result["discount_percent_computed"], 10.0)
        self.assertEqual(result["total"], 18000000.0)

    def test_amount_discount_calculation(self):
        """
        Chứng minh chiết khấu theo số tiền cố định (VNĐ):
        Số lượng: 1, Đơn giá: 15.000.000 đ => Thành tiền gốc = 15.000.000 đ
        Chiết khấu số tiền: 3.500.000 đ
        => Tiền chiết khấu dòng = 3.500.000 đ
        => Thành tiền sau chiết khấu = 11.500.000 đ
        => Tỷ lệ chiết khấu tương ứng = 23.33%
        """
        item = {
            "quantity": 1,
            "unit_price": 15000000,
            "discount_type": DISCOUNT_TYPE_AMOUNT,
            "discount_value": 3500000.0
        }

        result = self.db.calculate_line_item(item)

        self.assertEqual(result["subtotal"], 15000000.0)
        self.assertEqual(result["discount_amount"], 3500000.0)
        self.assertEqual(result["total"], 11500000.0)
        self.assertAlmostEqual(result["discount_percent_computed"], 23.33, places=2)

    def test_discount_capped_at_line_subtotal(self):
        """
        Chứng minh chiết khấu không thể vượt quá giá trị thành tiền gốc
        (tránh âm tiền gây thất thoát doanh số):
        Gốc = 5.000.000 đ, Nhập chiết khấu = 8.000.000 đ
        => Tiền chiết khấu được chặn tối đa = 5.000.000 đ
        => Thành tiền sau chiết khấu = 0 đ (không bị âm)
        """
        item = {
            "quantity": 1,
            "unit_price": 5000000,
            "discount_type": DISCOUNT_TYPE_AMOUNT,
            "discount_value": 8000000.0
        }

        result = self.db.calculate_line_item(item)
        self.assertEqual(result["subtotal"], 5000000.0)
        self.assertEqual(result["discount_amount"], 5000000.0)
        self.assertEqual(result["total"], 0.0)


if __name__ == "__main__":
    unittest.main()
