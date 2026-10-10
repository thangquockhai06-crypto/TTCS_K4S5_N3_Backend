"""
Kiểm thử Tiêu chí 3 (Acceptance Criteria 3) - Ticket SCRUM-54:
"Lead chuyển sang trạng thái Đã chuyển đổi và không sửa được nữa"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database, STATUS_CONVERTED, STATUS_QUALIFIED


class TestAC3ImmutableLock(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_lead_status_becomes_converted_and_is_locked(self):
        """
        Chứng minh sau khi chuyển đổi:
        1. Trạng thái của Lead đổi thành CONVERTED ("Đã chuyển đổi")
        2. Cờ khóa is_locked đổi thành True
        3. Ghi nhận thời điểm và người thực hiện chuyển đổi
        """
        lead_id = "LEAD-101"
        self.assertEqual(self.db.get_lead(lead_id)["status"], STATUS_QUALIFIED)

        result = self.db.convert_lead(lead_id, user_id="usr-01")
        lead = result["lead"]

        self.assertEqual(lead["status"], STATUS_CONVERTED)
        self.assertTrue(lead["is_locked"])
        self.assertIsNotNone(lead["converted_at"])
        self.assertEqual(lead["converted_by_id"], "usr-01")

    def test_update_lead_is_strictly_forbidden_after_conversion(self):
        """
        Chứng minh KHÓA BẢO VỆ BẤT BIẾN:
        Mọi cố gắng cập nhật dữ liệu của Lead sau khi đã chuyển đổi
        đều BỊ CHẶN ĐỨNG và ném ra PermissionError.
        Dữ liệu không hề bị thay đổi.
        """
        lead_id = "LEAD-101"
        original_company_name = self.db.get_lead(lead_id)["company_name"]

        # Chuyển đổi lead
        self.db.convert_lead(lead_id, user_id="usr-01")

        # Cố gắng sửa đổi thông tin công ty và ngân sách của lead đã chuyển đổi
        with self.assertRaises(PermissionError) as context:
            self.db.update_lead(
                lead_id,
                {
                    "company_name": "Tên Công Ty Giả Mạo Bị Sửa Lén",
                    "estimated_value": 9999999999
                },
                user_id="usr-01"
            )

        # Kiểm tra thông điệp báo lỗi rõ ràng về ràng buộc tiêu chí 3
        self.assertIn("RÀNG BUỘC TIÊU CHÍ 3", str(context.exception))
        self.assertIn("ĐÃ BỊ KHÓA BẤT BIẾN", str(context.exception))

        # Dữ liệu của lead không hề bị suy suyển
        lead_check = self.db.get_lead(lead_id)
        self.assertEqual(lead_check["company_name"], original_company_name)

    def test_pre_existing_converted_lead_is_also_locked(self):
        """
        Kiểm tra lead mẫu LEAD-105 (đã chuyển đổi trước đó trong dữ liệu demo)
        cũng được bảo vệ khóa và không thể chỉnh sửa.
        """
        lead_105 = self.db.get_lead("LEAD-105")
        self.assertEqual(lead_105["status"], STATUS_CONVERTED)
        self.assertTrue(lead_105["is_locked"])

        with self.assertRaises(PermissionError):
            self.db.update_lead("LEAD-105", {"phone": "0999999999"})

    def test_re_converting_already_converted_lead_is_blocked(self):
        """
        Chứng minh lead đã chuyển đổi không thể bị chuyển đổi lần 2 (chống duplicate).
        """
        lead_id = "LEAD-101"
        self.db.convert_lead(lead_id, user_id="usr-01")

        with self.assertRaises(ValueError) as context:
            self.db.convert_lead(lead_id, user_id="usr-01")

        self.assertIn("đã được chuyển đổi trước đó", str(context.exception))


if __name__ == "__main__":
    unittest.main()
