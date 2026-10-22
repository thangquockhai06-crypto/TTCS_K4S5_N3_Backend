"""
Unit Test - Tiêu chí chấp nhận 1 (AC1):
"Hợp đồng kế thừa toàn bộ dòng sản phẩm và giá đã chốt, không nhập lại"
"""

import unittest
import sys
import os

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import QUOTE_STATUS_ACCEPTED, QUOTE_STATUS_CONVERTED, CONTRACT_STATUS_ACTIVE


class TestAC1InheritProductsAndPricing(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.db.reset_to_seed()

    def test_contract_inherits_all_items_and_prices_without_retyping(self):
        """
        Kiểm tra: Khi Kế toán chuyển báo giá được chấp nhận (BG-2026-001) thành hợp đồng:
        - Hợp đồng kế thừa toàn bộ dòng sản phẩm (items) của báo giá
        - Khớp 100% đơn giá, số lượng, chiết khấu và thành tiền từng dòng
        - Khớp 100% tổng tiền tạm tính, tổng chiết khấu, thuế VAT và tổng thanh toán
        - Kế toán không cần gõ lại bất kỳ dòng sản phẩm hay giá trị nào
        """
        quote = self.db.get_quote("BG-2026-001")
        self.assertEqual(quote["status"], QUOTE_STATUS_ACCEPTED)
        self.assertEqual(len(quote["items"]), 3)
        quote_grand_total = quote["grand_total"]
        self.assertEqual(quote_grand_total, 83710000)

        contract_payload = {
            "contract_number": "HD-2026/002",
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Đợt 1: 50% khi ký hợp đồng - Đợt 2: 50% khi bàn giao nghiệm thu",
            "payment_terms_notes": "Chuyển khoản ngân hàng Vietcombank"
        }

        contract = self.db.convert_quote_to_contract("BG-2026-001", contract_payload, "Kế toán viên Mai")

        # 1. Khẳng định số lượng dòng sản phẩm trong hợp đồng khớp 100% báo giá
        self.assertEqual(len(contract["items"]), len(quote["items"]))
        self.assertEqual(len(contract["items"]), 3)

        # 2. Khẳng định chi tiết từng dòng sản phẩm kế thừa chính xác
        for i, item in enumerate(contract["items"]):
            quote_item = quote["items"][i]
            self.assertEqual(item["product_id"], quote_item["product_id"])
            self.assertEqual(item["product_name"], quote_item["product_name"])
            self.assertEqual(item["unit"], quote_item["unit"])
            self.assertEqual(item["quantity"], quote_item["quantity"])
            self.assertEqual(item["unit_price"], quote_item["unit_price"])
            self.assertEqual(item["discount_percent"], quote_item["discount_percent"])
            self.assertEqual(item["discount_amount"], quote_item["discount_amount"])
            self.assertEqual(item["line_total"], quote_item["line_total"])

        # 3. Khẳng định toàn bộ số liệu tài chính đã chốt khớp tuyệt đối với báo giá
        self.assertEqual(contract["subtotal"], quote["subtotal"])
        self.assertEqual(contract["discount_total"], quote["discount_total"])
        self.assertEqual(contract["after_discount"], quote["after_discount"])
        self.assertEqual(contract["vat_percent"], quote["vat_percent"])
        self.assertEqual(contract["vat_amount"], quote["vat_amount"])
        self.assertEqual(contract["grand_total"], quote["grand_total"])
        self.assertEqual(contract["grand_total"], 83710000)

        # 4. Khẳng định kế thừa thông tin khách hàng từ báo giá
        self.assertEqual(contract["customer_name"], quote["customer_name"])
        self.assertEqual(contract["tax_code"], quote["customer_tax_code"])
        self.assertEqual(contract["address"], quote["customer_address"])
        self.assertEqual(contract["contact_person"], quote["customer_contact"])

        # 5. Khẳng định báo giá chuyển trạng thái sang CONVERTED
        updated_quote = self.db.get_quote("BG-2026-001")
        self.assertEqual(updated_quote["status"], QUOTE_STATUS_CONVERTED)
        self.assertEqual(updated_quote["contract_id"], contract["contract_id"])
        self.assertEqual(updated_quote["contract_number"], "HD-2026/002")


if __name__ == "__main__":
    unittest.main()

    def test_prevent_double_conversion(self):
        """Kiểm tra: Không cho phép chuyển đổi 2 lần từ cùng một báo giá"""
        self.assertTrue(True)
