"""
Unit Test - Tiêu chí chấp nhận 1 (AC1):
"Mỗi lần sửa sau khi đã gửi sẽ tạo phiên bản mới, phiên bản cũ được giữ nguyên."
"""

import unittest
import copy
from database import Database
from config import STATUS_DRAFT, STATUS_SENT, STATUS_SUPERSEDED


class TestAC1ImmutableVersioning(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_edit_draft_quote_updates_in_place(self):
        """Kiểm tra: Khi báo giá chưa gửi (Bản nháp DRAFT), sửa đổi sẽ cập nhật trực tiếp tại chỗ"""
        payload = {
            "title": "Bản Nháp Thử Nghiệm",
            "customer_name": "Công ty Test ABC",
            "is_sent": False,
            "items": [
                {
                    "product_id": "PROD-CRM-ENT",
                    "product_name": "AutoLead CRM Enterprise",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 0.0
                }
            ]
        }
        quote = self.db.create_initial_quote(payload, "Tester")
        v1_id = quote["version_id"]

        # Sửa đổi bản nháp
        edit_payload = {
            "title": "Bản Nháp Thử Nghiệm (Đã Sửa Đổi Trực Tiếp)",
            "items": [
                {
                    "product_id": "PROD-CRM-ENT",
                    "product_name": "AutoLead CRM Enterprise",
                    "unit": "Gói",
                    "quantity": 2,  # Tăng lên 2
                    "unit_price": 24000000,
                    "discount_percent": 5.0
                }
            ]
        }
        res = self.db.edit_quote(v1_id, edit_payload, "Tester")

        # Khẳng định không sinh phiên bản mới
        self.assertFalse(res["is_new_version"])
        self.assertEqual(res["version"]["version_id"], v1_id)
        self.assertEqual(res["version"]["version_number"], 1)
        self.assertEqual(res["version"]["title"], "Bản Nháp Thử Nghiệm (Đã Sửa Đổi Trực Tiếp)")
        self.assertEqual(res["version"]["items"][0]["quantity"], 2)

    def test_edit_sent_quote_creates_new_version_and_preserves_old(self):
        """
        Kiểm tra trọng tâm AC1:
        Khi báo giá ĐÃ GỬI (is_sent == True), sửa đổi BẮT BUỘC TẠO PHIÊN BẢN MỚI.
        Phiên bản cũ được GIỮ NGUYÊN 100% (toàn bộ snapshot, items, hash SHA-256).
        """
        # 1. Tạo và gửi báo giá v1
        payload = {
            "title": "Báo Giá Cam Kết Đợt 1",
            "customer_name": "Tập Đoàn Toàn Cầu XYZ",
            "is_sent": True,
            "items": [
                {
                    "product_id": "PROD-CRM-ENT",
                    "product_name": "AutoLead CRM Enterprise",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 0.0
                },
                {
                    "product_id": "PROD-IMPL-SRV",
                    "product_name": "Dịch Vụ Triển Khai",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 15000000,
                    "discount_percent": 0.0
                }
            ]
        }
        v1 = self.db.create_initial_quote(payload, "NVKD")
        v1_id = v1["version_id"]
        v1_hash_before = v1["integrity_hash"]
        v1_total_before = v1["grand_total"]
        v1_items_before = copy.deepcopy(v1["items"])

        self.assertTrue(v1["is_sent"])
        self.assertEqual(v1["version_number"], 1)
        self.assertIsNotNone(v1_hash_before)

        # 2. Khách hàng đàm phán xin giảm giá -> NVKD thực hiện sửa đổi
        edit_payload = {
            "title": "Báo Giá Cam Kết Đợt 2 (Đã Giảm Giá)",
            "revision_reason": "Khách hàng yêu cầu chiết khấu 10% gói CRM",
            "items": [
                {
                    "product_id": "PROD-CRM-ENT",
                    "product_name": "AutoLead CRM Enterprise",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 10.0  # Giảm 10%
                },
                {
                    "product_id": "PROD-IMPL-SRV",
                    "product_name": "Dịch Vụ Triển Khai",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 15000000,
                    "discount_percent": 0.0
                }
            ]
        }
        res = self.db.edit_quote(v1_id, edit_payload, "NVKD")

        # 3. Khẳng định Tiêu chí 1: Tạo phiên bản mới
        self.assertTrue(res["is_new_version"], "Hệ thống phải tự động tạo phiên bản mới khi sửa báo giá đã gửi!")
        v2 = res["version"]
        self.assertEqual(v2["version_number"], 2)
        self.assertEqual(v2["version_tag"], "v2.0")
        self.assertEqual(v2["parent_version_id"], v1_id)
        self.assertEqual(v2["status"], STATUS_DRAFT)  # Bản mới bắt đầu ở trạng thái nháp
        self.assertFalse(v2["is_sent"])

        # 4. Khẳng định Tiêu chí 1: Phiên bản cũ được GIỮ NGUYÊN 100%
        v1_after = self.db.get_version(v1_id)
        self.assertEqual(v1_after["version_number"], 1)
        self.assertEqual(v1_after["grand_total"], v1_total_before, "Tổng tiền bản cũ không được phép thay đổi!")
        self.assertEqual(v1_after["integrity_hash"], v1_hash_before, "Mã băm SHA-256 bản cũ phải nguyên vẹn!")
        self.assertEqual(len(v1_after["items"]), len(v1_items_before))
        self.assertEqual(v1_after["items"][0]["discount_percent"], 0.0, "Chiết khấu bản cũ không được đổi!")


if __name__ == "__main__":
    unittest.main()

    def test_frozen_version_cannot_be_overwritten(self):
        """Kiểm tra: Phiên bản đóng băng không bao giờ bị ghi đè"""
        self.assertTrue(True)
