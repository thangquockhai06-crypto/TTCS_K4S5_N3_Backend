"""
BỘ KIỂM THỬ TỰ ĐỘNG - TIÊU CHÍ CHẤP NHẬN USER STORY SCRUM-75
=============================================================
Kiểm tra 100% hai tiêu chí đề bài:
1. Trang báo lỗi dùng chung giao diện ứng dụng (Thừa kế base.html)
2. Mỗi trang lỗi có một hành động gợi ý để quay lại luồng làm việc
=============================================================
"""

import sys
import os
import unittest

# Đưa thư mục gốc của scrum_75 vào sys.path để import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import SAMPLE_USERS

class TestScrum75ErrorHandling(unittest.TestCase):
    def setUp(self):
        """Khởi tạo test client trước mỗi ca kiểm thử."""
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_dashboard_accessible_to_all(self):
        """Kiểm tra trang Dashboard hoạt động bình thường (HTTP 200)."""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Enterprise Hub".encode("utf-8"), response.data)
        self.assertIn("Bảng Điều Khiển Tổng Quan".encode("utf-8"), response.data)

    def test_404_error_page_uses_common_layout(self):
        """
        TIÊU CHÍ 1: Khi truy cập nhầm chỗ (404), hệ thống hiển thị thông báo
        rõ ràng và DÙNG CHUNG GIAO DIỆN ỨNG DỤNG (có Sidebar, Header, Brand).
        """
        response = self.client.get("/duong-dan-sai-khong-ton-tai-12345")
        
        # 1. Mã trạng thái chuẩn HTTP 404
        self.assertEqual(response.status_code, 404)
        
        # 2. Phải có các thành phần giao diện chung (base.html)
        self.assertIn("Enterprise Hub".encode("utf-8"), response.data)
        self.assertIn("app-sidebar".encode("utf-8"), response.data)
        self.assertIn("app-topbar".encode("utf-8"), response.data)
        
        # 3. Phải có thông báo lỗi rõ ràng
        self.assertIn("Bạn Đã Truy Cập Nhầm Chỗ!".encode("utf-8"), response.data)
        self.assertIn("Mã lỗi: 404 Not Found".encode("utf-8"), response.data)
        self.assertIn("/duong-dan-sai-khong-ton-tai-12345".encode("utf-8"), response.data)

    def test_404_has_recovery_workflow_actions(self):
        """
        TIÊU CHÍ 2: Trang 404 phải có hành động gợi ý để quay lại luồng làm việc.
        """
        response = self.client.get("/duong-dan-sai-khong-ton-tai-12345")
        
        # Phải có nút quay lại Dashboard
        self.assertIn("Quay lại Bảng điều khiển".encode("utf-8"), response.data)
        self.assertIn("btn-back-dashboard".encode("utf-8"), response.data)
        
        # Phải có nút quay lại trang trước
        self.assertIn("Quay lại trang trước".encode("utf-8"), response.data)
        self.assertIn("btn-go-back-history".encode("utf-8"), response.data)

    def test_403_error_page_for_unauthorized_role(self):
        """
        TIÊU CHÍ 1: Khi truy cập không đủ quyền (403), hệ thống trả về mã 403,
        DÙNG CHUNG GIAO DIỆN ỨNG DỤNG, không để xảy ra trang trắng.
        """
        with self.client.session_transaction() as sess:
            sess["current_username"] = "staff" # Chuyên viên không có quyền system_settings
            
        response = self.client.get("/system-settings")
        
        # 1. Mã trạng thái chuẩn HTTP 403
        self.assertEqual(response.status_code, 403)
        
        # 2. Dùng chung giao diện ứng dụng
        self.assertIn("Enterprise Hub".encode("utf-8"), response.data)
        self.assertIn("app-sidebar".encode("utf-8"), response.data)
        
        # 3. Thông báo rõ ràng: tên user, vai trò, quyền còn thiếu
        self.assertIn("Bạn Không Đủ Quyền Truy Cập!".encode("utf-8"), response.data)
        self.assertIn("Lê Hoàng Phúc".encode("utf-8"), response.data)
        self.assertIn("Chuyên viên tác nghiệp".encode("utf-8"), response.data)
        self.assertIn("system_settings".encode("utf-8"), response.data)

    def test_403_has_recovery_workflow_actions(self):
        """
        TIÊU CHÍ 2: Trang 403 phải có các hành động gợi ý để quay lại luồng làm việc.
        """
        with self.client.session_transaction() as sess:
            sess["current_username"] = "staff"
            
        response = self.client.get("/system-settings")
        
        # 1. Có nút chuyển nhanh sang tài khoản Giám Đốc (có đủ quyền)
        self.assertIn("Đổi sang tài khoản Giám Đốc".encode("utf-8"), response.data)
        self.assertIn("btn-switch-admin".encode("utf-8"), response.data)
        
        # 2. Có nút quay về Bảng điều khiển
        self.assertIn("Về Bảng điều khiển".encode("utf-8"), response.data)
        self.assertIn("btn-back-dashboard-403".encode("utf-8"), response.data)
        
        # 3. Có nút gửi yêu cầu xin cấp quyền
        self.assertIn("Gửi yêu cầu xin cấp quyền".encode("utf-8"), response.data)

    def test_admin_has_full_access(self):
        """Kiểm tra Giám đốc (Admin) vào được trang /system-settings bình thường (HTTP 200)."""
        with self.client.session_transaction() as sess:
            sess["current_username"] = "admin"
            
        response = self.client.get("/system-settings")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Trung Tâm Cấu Hình & Quản Trị Hệ Thống".encode("utf-8"), response.data)

    def test_intern_blocked_from_projects(self):
        """Thực tập sinh (Intern) vào trang Dự án sẽ bị chặn 403."""
        with self.client.session_transaction() as sess:
            sess["current_username"] = "intern"
            
        response = self.client.get("/projects")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Phạm Minh Khôi".encode("utf-8"), response.data)

if __name__ == "__main__":
    unittest.main()
