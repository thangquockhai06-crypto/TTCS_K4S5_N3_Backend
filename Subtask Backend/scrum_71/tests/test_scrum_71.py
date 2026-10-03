"""
Kiểm thử tự động cho Subtask SCRUM-71 (Đặt lại mật khẩu qua Email)
"""

import sys
import os
import unittest

# Import app local
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app
from database import REDIS_TOKEN_STORE, SENT_EMAIL_LOGS, SAMPLE_USERS, get_reset_token


class TestScrum71PasswordReset(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        REDIS_TOKEN_STORE.clear()
        SENT_EMAIL_LOGS.clear()

    def test_forgot_password_valid_email(self):
        """Kiểm thử gửi yêu cầu đặt lại mật khẩu với email hợp lệ."""
        response = self.client.post("/api/v1/auth/forgot-password", json={
            "email": "saleman@nexuscrm.vn"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("30 phút", data["message"])
        self.assertEqual(len(SENT_EMAIL_LOGS), 1)
        self.assertEqual(SENT_EMAIL_LOGS[0]["recipient"], "saleman@nexuscrm.vn")

    def test_forgot_password_non_existent_email_anti_enumeration(self):
        """Kiểm thử Anti-Enumeration: email không tồn tại vẫn trả về cùng thông báo."""
        response = self.client.post("/api/v1/auth/forgot-password", json={
            "email": "unknown_hacker@external.com"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("30 phút", data["message"])
        # Không sinh email nhưng thông báo trả về giống hệt 100%
        self.assertEqual(len(SENT_EMAIL_LOGS), 0)

    def test_reset_password_success_and_single_use(self):
        """Kiểm thử đặt lại mật khẩu thành công và tính năng liên kết chỉ dùng 1 lần."""
        # 1. Gửi forgot-password
        self.client.post("/api/v1/auth/forgot-password", json={
            "email": "saleman@nexuscrm.vn"
        })
        token = SENT_EMAIL_LOGS[0]["token"]

        # 2. Đặt lại mật khẩu thành công
        reset_response = self.client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "NewSecretPassword123!"
        })
        self.assertEqual(reset_response.status_code, 200)
        self.assertTrue(reset_response.get_json()["success"])

        # 3. Thử dùng lại token lần 2 (Single-use restriction) -> Phải thất bại 400
        second_reset_response = self.client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "AnotherPassword123!"
        })
        self.assertEqual(second_reset_response.status_code, 400)
        self.assertIn("không hợp lệ hoặc đã hết hạn", second_reset_response.get_json()["message"])


if __name__ == "__main__":
    unittest.main()
