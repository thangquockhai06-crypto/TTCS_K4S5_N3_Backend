"""
Unit Test - Tiêu chí chấp nhận 4 (AC4):
"Số hợp đồng là duy nhất"
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database, DuplicateContractNumberError, InvalidQuoteStatusError


class TestAC4UniqueContractNumber(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.db.reset_to_seed()

    def test_duplicate_contract_number_rejected(self):
        """
        Kiểm tra: Hệ thống đã tồn tại hợp đồng số 'HD-2026/001'.
        Khi Kế toán cố gắng nhập số hợp đồng 'HD-2026/001' cho báo giá mới,
        hệ thống PHẢI từ chối và ném ra ngoại lệ DuplicateContractNumberError.
        """
        # Kiểm tra HĐ mẫu đã có trong hệ thống
        existing_contract = self.db.get_contract_by_number("HD-2026/001")
        self.assertIsNotNone(existing_contract)

        payload = {
            "contract_number": "HD-2026/001",  # TRÙNG VỚI SỐ HỢP ĐỒNG ĐÃ CÓ
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Thanh toán 100% trong 7 ngày"
        }

        with self.assertRaises(DuplicateContractNumberError) as ctx:
            self.db.convert_quote_to_contract("BG-2026-001", payload)

        self.assertIn("đã tồn tại trong hệ thống", str(ctx.exception))
        self.assertIn("Vui lòng nhập số hợp đồng duy nhất", str(ctx.exception))

    def test_case_insensitive_and_whitespace_duplicate_rejected(self):
        """
        Kiểm tra: Ràng buộc duy nhất không bị qua mặt bởi chữ hoa/thường hoặc khoảng trắng thừa
        (Ví dụ: '  hd-2026/001  ' vẫn bị phát hiện là trùng với 'HD-2026/001')
        """
        payload = {
            "contract_number": "   hd-2026/001   ",
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Net 30"
        }

        with self.assertRaises(DuplicateContractNumberError):
            self.db.convert_quote_to_contract("BG-2026-001", payload)

    def test_check_contract_number_availability_api(self):
        """Kiểm tra: Hàm kiểm tra tính khả dụng của số hợp đồng (Check Availability API)"""
        # Số đã tồn tại -> Not available
        res1 = self.db.check_contract_number_availability("HD-2026/001")
        self.assertFalse(res1["available"])
        self.assertIn("đã tồn tại", res1["message"])

        # Số mới chưa ai dùng -> Available
        res2 = self.db.check_contract_number_availability("HD-2026/999")
        self.assertTrue(res2["available"])
        self.assertIn("hợp lệ", res2["message"])

    def test_unique_contract_number_succeeds(self):
        """Kiểm tra: Khi nhập số hợp đồng duy nhất (ví dụ: HD-2026/002), chuyển đổi thành công"""
        payload = {
            "contract_number": "HD-2026/002",  # Duy nhất
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Net 30"
        }
        contract = self.db.convert_quote_to_contract("BG-2026-001", payload)
        self.assertEqual(contract["contract_number"], "HD-2026/002")

        # Ngay sau đó, 'HD-2026/002' đã trở thành số bị chiếm dụng
        res = self.db.check_contract_number_availability("HD-2026/002")
        self.assertFalse(res["available"])

    def test_cannot_convert_unaccepted_quote(self):
        """Kiểm tra: Báo giá chưa chấp nhận (trạng thái SENT hoặc DRAFT) không được phép chuyển HĐ"""
        payload = {
            "contract_number": "HD-2026/008",
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Net 30"
        }
        # BG-2026-004 đang ở trạng thái SENT (Chưa được khách chấp nhận)
        with self.assertRaises(InvalidQuoteStatusError) as ctx:
            self.db.convert_quote_to_contract("BG-2026-004", payload)
        self.assertIn("Chỉ những báo giá đã được khách hàng CHẤP NHẬN", str(ctx.exception))

    def test_cannot_convert_already_converted_quote(self):
        """Kiểm tra: Báo giá đã từng chuyển HĐ không thể chuyển lần thứ hai"""
        payload = {
            "contract_number": "HD-2026/009",
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Net 30"
        }
        # BG-2026-003 đã ở trạng thái CONVERTED
        with self.assertRaises(InvalidQuoteStatusError) as ctx:
            self.db.convert_quote_to_contract("BG-2026-003", payload)
        self.assertIn("đã được chuyển thành hợp đồng trước đó", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
