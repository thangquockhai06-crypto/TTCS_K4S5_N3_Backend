"""
Unit Test - Tiêu chí chấp nhận 2 (AC2):
"So sánh cạnh nhau hai phiên bản để thấy đã thay đổi gì."
"""

import unittest
from database import Database


class TestAC2SideBySideDiff(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_side_by_side_diff_detects_all_changes(self):
        """
        Kiểm tra Động cơ so sánh Side-by-side phát hiện chính xác:
        - Sản phẩm Added, Removed, Modified, Unchanged
        - Độ lệch tài chính (Financial Delta)
        - Biến động điều khoản thương mại
        """
        # Phiên bản 1: Có sản phẩm A và sản phẩm B
        p1 = {
            "title": "Báo Giá v1.0",
            "customer_name": "Công ty Khách Hàng Beta",
            "is_sent": True,
            "payment_terms": "Thanh toán 100% trước khi bàn giao",
            "items": [
                {
                    "product_id": "PROD-A",
                    "product_name": "Sản Phẩm A (Giữ nguyên)",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 10000000,
                    "discount_percent": 0.0
                },
                {
                    "product_id": "PROD-B",
                    "product_name": "Sản Phẩm B (Sẽ bị sửa SL & giảm giá)",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 20000000,
                    "discount_percent": 0.0
                },
                {
                    "product_id": "PROD-C",
                    "product_name": "Sản Phẩm C (Sẽ bị xóa)",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 5000000,
                    "discount_percent": 0.0
                }
            ]
        }
        v1 = self.db.create_initial_quote(p1, "NVKD")
        v1_id = v1["version_id"]

        # Sửa đổi tạo Phiên bản 2:
        # - Giữ PROD-A
        # - Sửa PROD-B (tăng quantity lên 2, giảm giá 10%)
        # - Xóa PROD-C
        # - Thêm mới PROD-D
        # - Đổi điều khoản thanh toán
        p2 = {
            "title": "Báo Giá v2.0 (Đàm phán lại)",
            "payment_terms": "Tạm ứng 50%, 50% sau nghiệm thu",
            "revision_reason": "Thêm gói tích hợp mới, bỏ dịch vụ phụ và tăng số lượng",
            "items": [
                {
                    "product_id": "PROD-A",
                    "product_name": "Sản Phẩm A (Giữ nguyên)",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 10000000,
                    "discount_percent": 0.0
                },
                {
                    "product_id": "PROD-B",
                    "product_name": "Sản Phẩm B (Sẽ bị sửa SL & giảm giá)",
                    "unit": "Gói",
                    "quantity": 2,               # Đổi 1 -> 2
                    "unit_price": 20000000,
                    "discount_percent": 10.0      # Đổi 0% -> 10%
                },
                {
                    "product_id": "PROD-D",
                    "product_name": "Sản Phẩm D (Thêm mới)",
                    "unit": "Module",
                    "quantity": 1,
                    "unit_price": 8000000,
                    "discount_percent": 0.0
                }
            ]
        }
        res = self.db.edit_quote(v1_id, p2, "NVKD")
        v2_id = res["new_version_id"]

        # Thực thi Side-by-side Diff Engine
        diff = self.db.diff_versions(v1_id, v2_id)

        # 1. Kiểm tra thống kê phân loại
        stats = diff["stats"]
        self.assertEqual(stats["unchanged_count"], 1, "Phải có đúng 1 sản phẩm giữ nguyên (PROD-A)")
        self.assertEqual(stats["modified_count"], 1, "Phải có đúng 1 sản phẩm điều chỉnh (PROD-B)")
        self.assertEqual(stats["removed_count"], 1, "Phải có đúng 1 sản phẩm bị xóa (PROD-C)")
        self.assertEqual(stats["added_count"], 1, "Phải có đúng 1 sản phẩm thêm mới (PROD-D)")

        # 2. Kiểm tra chi tiết thay đổi dòng PROD-B
        mod_item = next(it for it in diff["items_diff"] if it["key"] == "PROD-B")
        self.assertEqual(mod_item["diff_type"], "MODIFIED")
        self.assertIn("quantity", mod_item["changes"])
        self.assertEqual(mod_item["changes"]["quantity"]["old"], 1)
        self.assertEqual(mod_item["changes"]["quantity"]["new"], 2)
        self.assertIn("discount_percent", mod_item["changes"])
        self.assertEqual(mod_item["changes"]["discount_percent"]["old"], 0.0)
        self.assertEqual(mod_item["changes"]["discount_percent"]["new"], 10.0)

        # 3. Kiểm tra chênh lệch tài chính (Financial Delta)
        fin = diff["financial_diff"]
        self.assertNotEqual(fin["grand_total"]["delta"], 0)
        self.assertIn("delta_percent", fin["grand_total"])

        # 4. Kiểm tra đối chiếu điều khoản
        meta = diff["metadata_diff"]
        self.assertTrue(meta["payment_terms"]["is_changed"])
        self.assertEqual(meta["payment_terms"]["old"], "Thanh toán 100% trước khi bàn giao")
        self.assertEqual(meta["payment_terms"]["new"], "Tạm ứng 50%, 50% sau nghiệm thu")


if __name__ == "__main__":
    unittest.main()
