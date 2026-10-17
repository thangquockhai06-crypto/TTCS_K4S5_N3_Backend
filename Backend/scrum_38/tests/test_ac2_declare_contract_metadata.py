"""
Unit Test - Tiêu chí chấp nhận 2 (AC2):
"Khai báo số hợp đồng, ngày ký, ngày hiệu lực, ngày hết hạn, điều khoản thanh toán"
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database, ContractValidationError


class TestAC2DeclareContractMetadata(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.db.reset_to_seed()

    def test_declare_required_metadata_success(self):
        """
        Kiểm tra: Khai báo đầy đủ và chính xác các thông tin pháp lý bắt buộc:
        - Số hợp đồng: HD-2026/005
        - Ngày ký: 2026-10-17
        - Ngày hiệu lực: 2026-10-17
        - Ngày hết hạn: 2027-10-16
        - Điều khoản thanh toán: Thanh toán 100% trong vòng 7 ngày làm việc sau khi ký
        """
        payload = {
            "contract_number": "HD-2026/005",
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Thanh toán 100% trong vòng 7 ngày làm việc sau khi ký",
            "payment_terms_notes": "Chuyển khoản đủ trước khi bàn giao license"
        }
        contract = self.db.convert_quote_to_contract("BG-2026-001", payload, "Kế toán viên Mai")

        self.assertEqual(contract["contract_number"], "HD-2026/005")
        self.assertEqual(contract["signed_date"], "2026-10-17")
        self.assertEqual(contract["effective_date"], "2026-10-17")
        self.assertEqual(contract["expiration_date"], "2027-10-16")
        self.assertEqual(contract["payment_terms"], "Thanh toán 100% trong vòng 7 ngày làm việc sau khi ký")
        self.assertEqual(contract["payment_terms_notes"], "Chuyển khoản đủ trước khi bàn giao license")

    def test_missing_contract_number_raises_error(self):
        """Kiểm tra: Bỏ trống số hợp đồng sẽ báo lỗi ContractValidationError"""
        payload = {
            "contract_number": "",
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Thanh toán 100% trong 7 ngày"
        }
        with self.assertRaises(ContractValidationError) as ctx:
            self.db.convert_quote_to_contract("BG-2026-001", payload)
        self.assertIn("Số hợp đồng là trường bắt buộc", str(ctx.exception))

    def test_missing_dates_raises_error(self):
        """Kiểm tra: Bỏ trống ngày ký hoặc ngày hiệu lực hoặc ngày hết hạn sẽ báo lỗi"""
        # Thiếu ngày ký
        payload1 = {
            "contract_number": "HD-2026/006",
            "signed_date": "",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": "Net 30"
        }
        with self.assertRaises(ContractValidationError):
            self.db.convert_quote_to_contract("BG-2026-001", payload1)

        # Thiếu ngày hết hạn
        payload2 = {
            "contract_number": "HD-2026/006",
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "",
            "payment_terms": "Net 30"
        }
        with self.assertRaises(ContractValidationError):
            self.db.convert_quote_to_contract("BG-2026-001", payload2)

    def test_missing_payment_terms_raises_error(self):
        """Kiểm tra: Bỏ trống điều khoản thanh toán sẽ báo lỗi"""
        payload = {
            "contract_number": "HD-2026/006",
            "signed_date": "2026-10-17",
            "effective_date": "2026-10-17",
            "expiration_date": "2027-10-16",
            "payment_terms": ""
        }
        with self.assertRaises(ContractValidationError) as ctx:
            self.db.convert_quote_to_contract("BG-2026-001", payload)
        self.assertIn("Điều khoản thanh toán là trường bắt buộc", str(ctx.exception))

    def test_effective_date_after_expiration_date_raises_error(self):
        """Kiểm tra: Ngày hiệu lực sau ngày hết hạn sẽ báo lỗi không hợp lệ"""
        payload = {
            "contract_number": "HD-2026/007",
            "signed_date": "2026-10-17",
            "effective_date": "2027-10-17",
            "expiration_date": "2026-10-16",  # Ngày hết hạn trước ngày hiệu lực -> LỖI
            "payment_terms": "Net 30"
        }
        with self.assertRaises(ContractValidationError) as ctx:
            self.db.convert_quote_to_contract("BG-2026-001", payload)
        self.assertIn("không được sau ngày hết hạn", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
