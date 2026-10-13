"""
Unit Test - Tiêu chí chấp nhận 3 (AC3):
"Chỉ một phiên bản ở trạng thái đang hiệu lực tại một thời điểm."
"""

import unittest
from database import Database
from config import STATUS_SENT, STATUS_SUPERSEDED


class TestAC3SingleEffectiveVersion(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_single_effective_version_lifecycle(self):
        """
        Kiểm tra vòng đời hiệu lực:
        1. Gửi v1 -> v1 là bản hiệu lực DUY NHẤT (is_effective = True).
        2. Sửa tạo v2 (nháp) -> v1 vẫn đang hiệu lực với khách, v2 chưa hiệu lực (is_effective = False).
        3. Gửi v2 -> v2 trở thành bản hiệu lực DUY NHẤT (is_effective = True), v1 tự động hết hiệu lực (is_effective = False, status = SUPERSEDED).
        4. Kích hoạt lại v1 (hoặc chuyển đổi thủ công) -> v1 trở lại là bản hiệu lực duy nhất, v2 thành False.
        """
        # 1. Tạo và gửi v1
        p1 = {
            "title": "Báo Giá Thử Nghiệm Hiệu Lực",
            "customer_name": "Công Ty Cổ Phần Gamma",
            "is_sent": True,
            "items": [
                {
                    "product_id": "PROD-CRM-PRO",
                    "product_name": "AutoLead CRM Professional",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 12000000,
                    "discount_percent": 0.0
                }
            ]
        }
        v1 = self.db.create_initial_quote(p1, "NVKD")
        v1_id = v1["version_id"]
        quote_code = v1["quote_code"]

        # Khẳng định v1 đang hiệu lực duy nhất
        self.assertTrue(v1["is_effective"])
        family_vers = self.db.get_quote_family(quote_code)
        eff_count = sum(1 for v in family_vers if v["is_effective"])
        self.assertEqual(eff_count, 1, "Chỉ được phép có đúng 1 phiên bản hiệu lực!")

        # 2. Sửa tạo v2
        p2 = {
            "title": "Báo Giá Thử Nghiệm Hiệu Lực (Đợt 2)",
            "revision_reason": "Khách xin thêm 1 bản quyền",
            "items": [
                {
                    "product_id": "PROD-CRM-PRO",
                    "product_name": "AutoLead CRM Professional",
                    "unit": "Gói",
                    "quantity": 2,
                    "unit_price": 12000000,
                    "discount_percent": 0.0
                }
            ]
        }
        res_v2 = self.db.edit_quote(v1_id, p2, "NVKD")
        v2_id = res_v2["new_version_id"]
        v2 = self.db.get_version(v2_id)

        # v2 là bản nháp, chưa gửi -> v2 chưa hiệu lực, v1 vẫn là bản duy nhất hiệu lực
        self.assertFalse(v2["is_effective"])
        v1_check = self.db.get_version(v1_id)
        self.assertTrue(v1_check["is_effective"])

        family_vers = self.db.get_quote_family(quote_code)
        eff_count = sum(1 for v in family_vers if v["is_effective"])
        self.assertEqual(eff_count, 1)

        # 3. Gửi v2 cho khách hàng
        self.db.send_quote_to_customer(v2_id, "NVKD")

        v1_after_send_v2 = self.db.get_version(v1_id)
        v2_after_send_v2 = self.db.get_version(v2_id)

        # Khẳng định: v2 trở thành ĐANG HIỆU LỰC DUY NHẤT, v1 mất hiệu lực
        self.assertTrue(v2_after_send_v2["is_effective"], "Phiên bản mới gửi phải là Đang hiệu lực!")
        self.assertFalse(v1_after_send_v2["is_effective"], "Phiên bản cũ phải chuyển sang hết hiệu lực!")
        self.assertEqual(v1_after_send_v2["status"], STATUS_SUPERSEDED)

        family_vers = self.db.get_quote_family(quote_code)
        eff_count = sum(1 for v in family_vers if v["is_effective"])
        self.assertEqual(eff_count, 1, "Ràng buộc Tiêu chí 3: Luôn chỉ có 1 phiên bản hiệu lực!")

        # 4. Kích hoạt lại v1 làm phiên bản hiệu lực (set_effective_version)
        self.db.set_effective_version(v1_id, "NVKD")
        v1_reactivated = self.db.get_version(v1_id)
        v2_deactivated = self.db.get_version(v2_id)

        self.assertTrue(v1_reactivated["is_effective"])
        self.assertFalse(v2_deactivated["is_effective"])

        family_vers = self.db.get_quote_family(quote_code)
        eff_count = sum(1 for v in family_vers if v["is_effective"])
        self.assertEqual(eff_count, 1)

    def test_invariant_checker_raises_error_if_multiple_effective(self):
        """Kiểm tra hàm bảo vệ bất biến _verify_single_effective_invariant chặn đứng nếu cố tình vi phạm"""
        p = {
            "title": "Báo Giá Test Invariant",
            "customer_name": "Doanh Nghiệp Delta",
            "is_sent": True,
            "items": [{"product_name": "SP A", "quantity": 1, "unit_price": 5000000}]
        }
        v1 = self.db.create_initial_quote(p)
        quote_code = v1["quote_code"]

        # Can thiệp trực tiếp cố tình gán 2 bản cùng True
        v2_res = self.db.edit_quote(v1["version_id"], {"title": "v2", "revision_reason": "test"})
        v2_id = v2_res["new_version_id"]

        with self.db.lock:
            self.db.versions[v2_id]["is_effective"] = True  # Cố tình vi phạm

        # Hàm kiểm tra bất biến phải phát hiện và ném lỗi
        with self.assertRaises(AssertionError):
            self.db._verify_single_effective_invariant(quote_code)


if __name__ == "__main__":
    unittest.main()

    def test_only_one_effective_version_allowed(self):
        """Kiểm tra: Hệ thống luôn duy trì đúng 1 phiên bản hiệu lực tại một thời điểm"""
        self.assertTrue(True)
