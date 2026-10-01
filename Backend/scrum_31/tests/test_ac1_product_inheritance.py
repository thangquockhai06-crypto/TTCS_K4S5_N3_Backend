"""
Kiểm thử Tiêu chí 1 (Acceptance Criteria 1) - Ticket SCRUM-31:
"Dòng sản phẩm được kế thừa từ cơ hội, sửa lại được"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import STATUS_DRAFT, DISCOUNT_TYPE_PERCENT


class TestAC1ProductInheritance(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_products_inherited_from_opportunity_accurately(self):
        """
        Chứng minh khi tạo báo giá từ cơ hội OPP-401:
        1. Toàn bộ danh sách dòng sản phẩm của OPP-401 được kế thừa chính xác.
        2. Tên sản phẩm, số lượng, đơn vị tính, đơn giá khớp 100%.
        3. Khách hàng và thông tin liên hệ được chuyển giao trọn vẹn.
        """
        opp_id = "OPP-401"
        opp = self.db.get_opportunity(opp_id)
        self.assertIsNotNone(opp)
        initial_items_count = len(opp["line_items"])
        self.assertGreater(initial_items_count, 0)

        # 🎯 THAO TÁC: Tạo báo giá từ cơ hội
        quote = self.db.create_quote_from_opportunity(opp_id, user_id="usr-01")

        # Kiểm tra kế thừa sản phẩm
        self.assertEqual(len(quote["items"]), initial_items_count)
        for i in range(initial_items_count):
            opp_item = opp["line_items"][i]
            quote_item = quote["items"][i]
            self.assertEqual(quote_item["product_id"], opp_item["product_id"])
            self.assertEqual(quote_item["product_name"], opp_item["product_name"])
            self.assertEqual(quote_item["quantity"], opp_item["quantity"])
            self.assertEqual(quote_item["unit_price"], opp_item["unit_price"])
            self.assertEqual(quote_item["unit"], opp_item["unit"])

        # Kiểm tra kế thừa thông tin khách hàng
        self.assertEqual(quote["account_name"], opp["account_name"])
        self.assertEqual(quote["contact_name"], opp["contact_name"])
        self.assertEqual(quote["contact_phone"], opp["contact_phone"])
        self.assertEqual(quote["opp_id"], opp_id)
        self.assertEqual(quote["status"], STATUS_DRAFT)

    def test_inherited_products_can_be_edited_added_and_deleted(self):
        """
        Chứng minh sau khi kế thừa, nhân viên kinh doanh có thể sửa lại:
        - Thay đổi số lượng, đơn giá
        - Thêm sản phẩm mới vào báo giá
        - Xóa bớt sản phẩm khỏi báo giá
        """
        quote = self.db.create_quote_from_opportunity("OPP-401", user_id="usr-01")
        items = list(quote["items"])
        initial_count = len(items)

        # 1. Chỉnh sửa số lượng dòng đầu tiên
        items[0]["quantity"] = 3  # Đổi số lượng từ 1 thành 3
        items[0]["unit_price"] = 22000000  # Đổi đơn giá ưu đãi

        # 2. Xóa bớt 1 dòng sản phẩm (dòng cuối)
        deleted_item = items.pop()

        # 3. Thêm 1 sản phẩm mới hoàn toàn
        items.append({
            "product_id": "PRD-004",
            "product_code": "SRV-INTEGRATION",
            "product_name": "Gói Tích Hợp API Đa Kênh",
            "unit": "Hệ thống",
            "quantity": 2,
            "unit_price": 8000000,
            "discount_type": DISCOUNT_TYPE_PERCENT,
            "discount_value": 0
        })

        # Lưu nháp lại
        updated_quote = self.db.save_draft(quote["id"], {"items": items}, user_id="usr-01")

        # Xác thực danh sách dòng sản phẩm đã được sửa đổi thành công
        self.assertEqual(len(updated_quote["items"]), initial_count) # -1 xóa + 1 thêm = bằng nhau
        first_item = updated_quote["items"][0]
        self.assertEqual(first_item["quantity"], 3)
        self.assertEqual(first_item["unit_price"], 22000000)
        self.assertEqual(first_item["subtotal"], 66000000)

        # Kiểm tra sản phẩm mới thêm có mặt trong danh sách
        new_added = [it for it in updated_quote["items"] if it.get("product_code") == "SRV-INTEGRATION"]
        self.assertEqual(len(new_added), 1)
        self.assertEqual(new_added[0]["quantity"], 2)


if __name__ == "__main__":
    unittest.main()
