"""
Kiểm thử Tiêu chí 2 (Acceptance Criteria 2) - Ticket SCRUM-54:
"Dữ liệu lead được chuyển sang, không phải nhập lại"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database


class TestAC2DataInheritance(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_lead_data_fully_transferred_without_retyping(self):
        """
        Chứng minh toàn bộ dữ liệu phong phú của Lead:
        - Thông tin công ty: tên, MST, ngành nghề, địa chỉ, SĐT, email, website
        - Thông tin người liên hệ: họ tên, chức vụ, SĐT, email
        - Thông tin cơ hội: sản phẩm quan tâm, giá trị dự kiến, thời hạn chốt
        được chuyển đổi chính xác 100% sang Khách hàng, Người liên hệ và Cơ hội,
        người dùng không cần nhập lại bất kỳ thông tin nào đã hỏi trước đó.
        """
        lead = self.db.get_lead("LEAD-101")
        self.assertIsNotNone(lead)

        # Ghi nhận dữ liệu gốc của lead
        original_company_name = lead["company_name"]
        original_tax_id = lead["tax_id"]
        original_industry = lead["industry"]
        original_address = lead["address"]
        original_city = lead["city"]
        original_website = lead["website"]
        original_company_size = lead["company_size"]

        original_contact_name = lead["contact_name"]
        original_job_title = lead["job_title"]
        original_phone = lead["phone"]
        original_email = lead["email"]

        original_product = lead["interested_product"]
        original_estimated_value = lead["estimated_value"]
        original_expected_close_date = lead["expected_close_date"]

        # Thực hiện chuyển đổi mà không cần truyền bất kỳ tham số tùy biến nào
        # (Chứng minh hệ thống tự động kế thừa 100%)
        result = self.db.convert_lead("LEAD-101", user_id="usr-01")

        account = result["account"]
        contact = result["contact"]
        opportunity = result["opportunity"]

        # 1. KIỂM TRA DỮ LIỆU CHUYỂN SANG KHÁCH HÀNG DOANH NGHIỆP (ACCOUNT)
        self.assertEqual(account["name"], original_company_name)
        self.assertEqual(account["tax_id"], original_tax_id)
        self.assertEqual(account["industry"], original_industry)
        self.assertEqual(account["address"], original_address)
        self.assertEqual(account["city"], original_city)
        self.assertEqual(account["website"], original_website)
        self.assertEqual(account["company_size"], original_company_size)
        self.assertEqual(account["phone"], original_phone)
        self.assertEqual(account["email"], original_email)

        # 2. KIỂM TRA DỮ LIỆU CHUYỂN SANG NGƯỜI LIÊN HỆ (CONTACT)
        self.assertEqual(contact["full_name"], original_contact_name)
        self.assertEqual(contact["job_title"], original_job_title)
        self.assertEqual(contact["phone"], original_phone)
        self.assertEqual(contact["email"], original_email)
        self.assertTrue(contact["is_primary"])

        # 3. KIỂM TRA DỮ LIỆU CHUYỂN SANG CƠ HỘI BÁN HÀNG (OPPORTUNITY)
        self.assertEqual(opportunity["amount"], original_estimated_value)
        self.assertEqual(opportunity["product"], original_product)
        self.assertEqual(opportunity["close_date"], original_expected_close_date)
        self.assertIn(original_company_name, opportunity["name"])

        # 4. KIỂM TRA NGƯỜI PHỤ TRÁCH (OWNER) ĐƯỢC BẢO TOÀN
        self.assertEqual(account["owner_id"], lead["assigned_to_id"])
        self.assertEqual(contact["owner_id"], lead["assigned_to_id"])
        self.assertEqual(opportunity["owner_id"], lead["assigned_to_id"])


if __name__ == "__main__":
    unittest.main()
