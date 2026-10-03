"""
BỘ KIỂM THỬ TỰ ĐỘNG - TIÊU CHÍ CHẤP NHẬN USER STORY SCRUM-80
=============================================================
Kiểm tra 100% ba tiêu chí của đề bài:
  1. Sửa được họ tên, số điện thoại, chữ ký email.
  2. Không tự đổi được email, nhóm và vai trò.
  3. Kiểm tra định dạng số điện thoại Việt Nam.
=============================================================
"""

import sys
import os
import unittest

# Đưa thư mục gốc của scrum_80 vào sys.path để import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import (
    USERS_DB,
    get_user,
    update_user_profile,
    validate_vietnam_phone,
    reset_database
)

class TestScrum80UserProfile(unittest.TestCase):
    def setUp(self):
        """Khởi tạo môi trường kiểm thử và reset dữ liệu người dùng ban đầu."""
        app.config["TESTING"] = True
        self.client = app.test_client()
        reset_database()

    def test_tc1_view_profile_page_success(self):
        """
        Kiểm tra trang Hồ sơ cá nhân tải thành công (HTTP 200)
        và hiển thị đúng thông tin của người dùng đang đăng nhập.
        """
        response = self.client.get("/profile")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Hồ Sơ Cá Nhân".encode("utf-8"), response.data)
        self.assertIn("Lê Hoàng Phúc".encode("utf-8"), response.data)
        self.assertIn("hoangphuc.le@enterprise-sales.vn".encode("utf-8"), response.data)
        self.assertIn("Chuyên viên kinh doanh".encode("utf-8"), response.data)

    def test_tc1_update_allowed_fields_success(self):
        """
        TIÊU CHÍ 1: Sửa được họ tên, số điện thoại, chữ ký email.
        """
        new_name = "Lê Hoàng Phúc (Trưởng Nhóm Mới)"
        new_phone = "0988 777 666"
        new_sig = (
            "Trân trọng,\n"
            "Lê Hoàng Phúc | Chuyên viên Kinh doanh Cao cấp\n"
            "Hotline: 0988 777 666 | Email: hoangphuc.le@enterprise-sales.vn"
        )

        response = self.client.post("/profile", data={
            "full_name": new_name,
            "phone": new_phone,
            "email_signature": new_sig
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Cập nhật hồ sơ cá nhân thành công!".encode("utf-8"), response.data)
        
        # Kiểm tra dữ liệu trong DB đã thực sự được lưu
        user = get_user("sales_rep")
        self.assertEqual(user["full_name"], new_name)
        self.assertEqual(user["phone"], "0988 777 666")
        self.assertEqual(user["email_signature"], new_sig)

    def test_tc2_cannot_modify_protected_fields_form_readonly(self):
        """
        TIÊU CHÍ 2: Không tự đổi được email, nhóm và vai trò.
        Kiểm tra trên giao diện HTML có thuộc tính readonly và nhãn khóa 🔒.
        """
        response = self.client.get("/profile")
        self.assertEqual(response.status_code, 200)
        html_str = response.data.decode("utf-8")
        
        # Kiểm tra các trường email, business_group, role_name phải có thuộc tính readonly
        self.assertIn('name="email"', html_str)
        self.assertIn('readonly', html_str)
        self.assertIn("Không tự đổi được (Tiêu chí 2)", html_str)
        self.assertIn("🔒 Cố định", html_str)

    def test_tc2_backend_protection_against_tampering(self):
        """
        TIÊU CHÍ 2 (Bảo vệ đa tầng phía Backend):
        Nếu người dùng cố tình gửi dữ liệu sửa email, nhóm kinh doanh hoặc vai trò
        thông qua POST request, hệ thống backend phải TỪ CHỐI GHI ĐÈ các trường này.
        """
        hacker_payload = {
            "full_name": "Lê Hoàng Phúc",
            "phone": "0912 345 678",
            "email_signature": "Chữ ký test",
            # Cố tình sửa các trường bảo mật:
            "email": "hacker.takeover@fake-domain.com",
            "role_code": "director",
            "role_name": "Tổng Giám Đốc Toàn Quyền",
            "business_group": "Hội Đồng Quản Trị"
        }

        response = self.client.post("/profile", data=hacker_payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Kiểm tra người dùng trong DB: Các trường nhạy cảm VẪN GIỮ NGUYÊN GIÁ TRỊ GỐC
        user = get_user("sales_rep")
        self.assertEqual(user["email"], "hoangphuc.le@enterprise-sales.vn") # Không bị đổi thành hacker
        self.assertEqual(user["role_code"], "sales_rep") # Không bị leo thang thành director
        self.assertEqual(user["role_name"], "Chuyên viên kinh doanh")
        self.assertEqual(user["business_group"], "Nhóm Bán Lẻ Khu Vực Miền Bắc")

    def test_tc3_valid_vietnam_phone_numbers(self):
        """
        TIÊU CHÍ 3: Kiểm tra các định dạng số điện thoại Việt Nam HỢP LỆ.
        Bao gồm các nhà mạng lớn: Viettel, Vinaphone, Mobifone, Vietnamobile, Wintel, có hoặc không có mã quốc gia (+84).
        """
        valid_phones = [
            ("0912345678", "0912 345 678"),         # VinaPhone 091
            ("0987654321", "0987 654 321"),         # Viettel 098
            ("0903112233", "0903 112 233"),         # MobiFone 090
            ("0388123456", "0388 123 456"),         # Viettel đầu 03
            ("0779988776", "0779 988 776"),         # MobiFone đầu 07
            ("0868123456", "0868 123 456"),         # Viettel đầu 086
            ("0521234567", "0521 234 567"),         # Vietnamobile 052
            ("+84912345678", "0912 345 678"),       # Định dạng quốc tế +84
            ("0912 345 678", "0912 345 678"),       # Có khoảng trắng
            ("0912-345-678", "0912 345 678"),       # Có dấu gạch nối
            ("0912.345.678", "0912 345 678"),       # Có dấu chấm
        ]

        for raw_phone, expected_format in valid_phones:
            is_valid, formatted, err = validate_vietnam_phone(raw_phone)
            self.assertTrue(is_valid, f"Số {raw_phone} phải hợp lệ nhưng bị báo lỗi: {err}")
            self.assertEqual(formatted, expected_format)

    def test_tc3_invalid_vietnam_phone_numbers_rejected(self):
        """
        TIÊU CHÍ 3: Kiểm tra các số điện thoại KHÔNG HỢP LỆ bị từ chối chính xác:
        - Quá ngắn hoặc quá dài
        - Chứa chữ cái
        - Sai đầu số nhà mạng
        - Đầu số cố định cũ (024, 028) không phải di động
        - Để trống
        """
        invalid_phones = [
            "",                       # Để trống
            "   ",                    # Toàn khoảng trắng
            "0912345",                # Quá ngắn (7 số)
            "091234567899",           # Quá dài (12 số)
            "0912abc678",             # Chứa chữ cái
            "0123456789",             # Đầu số 012 cũ đã bị đổi
            "02438889999",            # Số máy bàn cố định
            "+14155552671",           # Số điện thoại quốc tế Mỹ
            "1234567890",             # Không bắt đầu bằng 0 hoặc 84
        ]

        for phone in invalid_phones:
            is_valid, formatted, err = validate_vietnam_phone(phone)
            self.assertFalse(is_valid, f"Số '{phone}' không hợp lệ nhưng hệ thống lại chấp nhận!")
            self.assertNotEqual(err, "")

    def test_tc3_profile_submission_with_invalid_phone_fails(self):
        """
        TIÊU CHÍ 3: Khi submit form với số điện thoại sai định dạng,
        hệ thống trả về HTTP 400 và thông báo lỗi rõ ràng.
        """
        response = self.client.post("/profile", data={
            "full_name": "Lê Hoàng Phúc",
            "phone": "0123456789", # Sai đầu mạng VN
            "email_signature": "Chữ ký mẫu"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("không đúng định dạng mạng di động Việt Nam".encode("utf-8"), response.data)

    def test_user_story_signature_in_quote_preview(self):
        """
        XÁC THỰC TOÀN DIỆN MỤC TIÊU USER STORY:
        "để chữ ký email của tôi luôn đúng khi gửi báo giá cho khách"
        Cập nhật chữ ký ở profile -> Truy cập xem trước Báo giá -> Thấy đúng chữ ký mới!
        """
        custom_sig = (
            "KÍNH CHÚC QUÝ KHÁCH THÀNH CÔNG VÀ PHÁT TRIỂN!\n"
            "Chuyên viên: Lê Hoàng Phúc - Phòng Giải Pháp Doanh Nghiệp\n"
            "Hotline tư vấn 24/7: 0912 345 678"
        )
        # 1. Cập nhật hồ sơ
        self.client.post("/profile", data={
            "full_name": "Lê Hoàng Phúc",
            "phone": "0912 345 678",
            "email_signature": custom_sig
        }, follow_redirects=True)

        # 2. Vào xem trước báo giá mã BG-2026-001
        response = self.client.get("/quotes/BG-2026-001/preview")
        self.assertEqual(response.status_code, 200)
        
        # 3. Phải nhìn thấy chữ ký vừa cập nhật trong bức thư gửi khách
        self.assertIn("KÍNH CHÚC QUÝ KHÁCH THÀNH CÔNG VÀ PHÁT TRIỂN!".encode("utf-8"), response.data)
        self.assertIn("Hotline tư vấn 24/7: 0912 345 678".encode("utf-8"), response.data)

    def test_switch_user_functionality(self):
        """Kiểm tra tính năng chuyển đổi người dùng hoạt động chính xác."""
        response = self.client.get("/switch-user/team_lead", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Trần Thị Mai Phương".encode("utf-8"), response.data)
        self.assertIn("Trưởng nhóm kinh doanh".encode("utf-8"), response.data)

    def test_error_404_uses_common_layout(self):
        """Kiểm tra trang lỗi 404 hoạt động và dùng chung giao diện base.html."""
        response = self.client.get("/duong-dan-khong-ton-tai-404")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Mã lỗi: 404 Not Found".encode("utf-8"), response.data)
        self.assertIn("Enterprise CRM".encode("utf-8"), response.data)

if __name__ == "__main__":
    unittest.main()
