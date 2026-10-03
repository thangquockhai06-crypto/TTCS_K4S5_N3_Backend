"""
Kiểm thử tự động cho Subtask SCRUM-72 (Đổi mật khẩu khi đang đăng nhập)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app
from database import ACTIVE_SESSIONS, SAMPLE_USERS, get_user_by_email


class TestScrum72ChangePassword(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_change_password_missing_current_password(self):
        """Kiểm thử lỗi khi thiếu mật khẩu hiện tại."""
        response = self.client.post("/api/v1/auth/change-password", json={
            "email": "saleman@nexuscrm.vn",
            "new_password": "ValidPass123!"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("mật khẩu hiện tại", response.get_json()["message"])

    def test_change_password_wrong_current_password(self):
        """Kiểm thử lỗi khi nhập sai mật khẩu hiện tại."""
        response = self.client.post("/api/v1/auth/change-password", json={
            "email": "saleman@nexuscrm.vn",
            "current_password": "WrongPassword999",
            "new_password": "ValidPass123!"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("không chính xác", response.get_json()["message"])

    def test_change_password_invalid_new_password_rules(self):
        """Kiểm thử validate mật khẩu mới (dưới 8 ký tự hoặc thiếu chữ/số)."""
        # Mật khẩu quá ngắn (< 8 ký tự)
        resp_short = self.client.post("/api/v1/auth/change-password", json={
            "email": "saleman@nexuscrm.vn",
            "current_password": "OldPassword123!",
            "new_password": "Pass1"
        })
        self.assertEqual(resp_short.status_code, 400)

        # Mật khẩu không có số
        resp_no_digit = self.client.post("/api/v1/auth/change-password", json={
            "email": "saleman@nexuscrm.vn",
            "current_password": "OldPassword123!",
            "new_password": "OnlyLettersHere"
        })
        self.assertEqual(resp_no_digit.status_code, 400)

    def test_change_password_success_and_session_revocation(self):
        """Kiểm thử đổi mật khẩu thành công và tự động thu hồi các phiên đăng nhập khác."""
        response = self.client.post("/api/v1/auth/change-password", json={
            "email": "saleman@nexuscrm.vn",
            "current_password": "OldPassword123!",
            "new_password": "NewSecurePass2026!",
            "current_session_id": "SESS-101"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("thành công", data["message"])
        self.assertGreaterEqual(data["revoked_other_sessions"], 1)

        # Kiểm tra phiên khác đã bị hủy (is_revoked = True)
        revoked_sessions = [s for s in ACTIVE_SESSIONS if s["user_id"] == "USR-003" and s["session_id"] != "SESS-101"]
        for sess in revoked_sessions:
            self.assertTrue(sess["is_revoked"])


if __name__ == "__main__":
    unittest.main()
