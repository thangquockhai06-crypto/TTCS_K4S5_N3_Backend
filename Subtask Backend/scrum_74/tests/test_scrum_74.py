"""
BỘ KIỂM THỬ TỰ ĐỘNG - XÁC THỰC 100% TIÊU CHÍ CHẤP NHẬN USER STORY SCRUM-74
=============================================================================
Mã Nhiệm Vụ: SCRUM-69 / SCRUM-74
Tiêu đề:
  "Là người dùng của hệ thống, tôi muốn thấy menu điều hướng đúng theo quyền của mình,
   để không bị rối bởi những chức năng mình không được dùng."

3 Tiêu chí chấp nhận được kiểm tra toàn diện:
  1. Mục menu không thuộc quyền thì không hiển thị (Lọc sạch khỏi DOM + chặn 403 backend)
  2. Hiển thị tên, vai trò và nhóm kinh doanh đang thuộc về
  3. Dùng được thuận tiện trên màn hình 360px (Responsive Mobile Hamburger & Drawer)
=============================================================================
"""

import sys
import os
import unittest

# Đưa thư mục gốc của scrum_74 vào sys.path để import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import SAMPLE_USERS, ALL_MENU_ITEMS, get_user_menu

class TestScrum74RBACNavigation(unittest.TestCase):
    def setUp(self):
        """Khởi tạo test client trước mỗi ca kiểm thử."""
        app.config["TESTING"] = True
        self.client = app.test_client()

    # =========================================================================
    # NHÓM 1: KIỂM THỬ TIÊU CHÍ 1 - LỌC MENU THEO VAI TRÒ (ẨN KHỎI DOM)
    # =========================================================================
    def test_director_sees_all_7_menu_items(self):
        """
        Ca 1: Giám đốc kinh doanh (Director) có toàn quyền -> Phải thấy đủ 7 mục menu.
        """
        with self.client.session_transaction() as sess:
            sess["current_username"] = "director"

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        # Kiểm tra đầy đủ 7 mục menu đều xuất hiện
        self.assertIn('data-menu-id="dashboard"', html)
        self.assertIn('data-menu-id="customers"', html)
        self.assertIn('data-menu-id="deals"', html)
        self.assertIn('data-menu-id="team_reports"', html)
        self.assertIn('data-menu-id="team_targets"', html)
        self.assertIn('data-menu-id="staff_management"', html)
        self.assertIn('data-menu-id="settings"', html)

        # Kiểm tra banner đếm menu
        self.assertIn("7 / 7 mục", html)

    def test_team_lead_sees_5_menu_items_and_hides_2(self):
        """
        Ca 2: Trưởng nhóm kinh doanh (Team Lead) -> Thấy đúng 5 mục menu.
        Mục 'Quản lý nhân sự' và 'Cấu hình hệ thống' phải BỊ LOẠI BỎ HOÀN TOÀN khỏi DOM.
        """
        with self.client.session_transaction() as sess:
            sess["current_username"] = "team_lead"

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        # 5 mục được phép thấy
        self.assertIn('data-menu-id="dashboard"', html)
        self.assertIn('data-menu-id="customers"', html)
        self.assertIn('data-menu-id="deals"', html)
        self.assertIn('data-menu-id="team_reports"', html)
        self.assertIn('data-menu-id="team_targets"', html)

        # 2 mục ngoài quyền: KHÔNG ĐƯỢC XUẤT HIỆN TRONG DOM
        self.assertNotIn('data-menu-id="staff_management"', html)
        self.assertNotIn('data-menu-id="settings"', html)
        self.assertNotIn('href="/staff-management"', html)
        self.assertNotIn('href="/settings"', html)

        self.assertIn("5 / 7 mục", html)

    def test_sales_rep_sees_3_menu_items_and_hides_4(self):
        """
        Ca 3: Chuyên viên kinh doanh (Sales Rep) -> Chỉ thấy 3 mục tác nghiệp.
        4 mục cấp quản lý/hệ thống phải bị loại bỏ hoàn toàn khỏi DOM.
        """
        with self.client.session_transaction() as sess:
            sess["current_username"] = "sales_rep"

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        # 3 mục được phép thấy
        self.assertIn('data-menu-id="dashboard"', html)
        self.assertIn('data-menu-id="customers"', html)
        self.assertIn('data-menu-id="deals"', html)

        # 4 mục ngoài quyền: KHÔNG ĐƯỢC XUẤT HIỆN TRONG DOM
        self.assertNotIn('data-menu-id="team_reports"', html)
        self.assertNotIn('data-menu-id="team_targets"', html)
        self.assertNotIn('data-menu-id="staff_management"', html)
        self.assertNotIn('data-menu-id="settings"', html)

        self.assertIn("3 / 7 mục", html)

    def test_intern_sees_only_1_menu_item(self):
        """
        Ca 4: Thực tập sinh kinh doanh (Intern) -> Chỉ thấy duy nhất 1 mục Bảng điều khiển.
        6 mục còn lại hoàn toàn không hiển thị.
        """
        with self.client.session_transaction() as sess:
            sess["current_username"] = "intern"

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        self.assertIn('data-menu-id="dashboard"', html)
        self.assertNotIn('data-menu-id="customers"', html)
        self.assertNotIn('data-menu-id="deals"', html)
        self.assertNotIn('data-menu-id="team_reports"', html)
        self.assertNotIn('data-menu-id="team_targets"', html)
        self.assertNotIn('data-menu-id="staff_management"', html)
        self.assertNotIn('data-menu-id="settings"', html)

        self.assertIn("1 / 7 mục", html)

    # =========================================================================
    # NHÓM 2: KIỂM THỬ TIÊU CHÍ 2 - HIỂN THỊ TÊN, VAI TRÒ, NHÓM KINH DOANH
    # =========================================================================
    def test_user_profile_card_shows_name_role_and_business_group(self):
        """
        Ca 5: Kiểm tra Thẻ Profile người dùng hiển thị đầy đủ 3 trường:
        1. Họ và tên
        2. Vai trò
        3. Nhóm kinh doanh đang thuộc về
        """
        # Thử nghiệm với Chuyên viên Lê Hoàng Phúc
        with self.client.session_transaction() as sess:
            sess["current_username"] = "sales_rep"

        response = self.client.get("/dashboard")
        html = response.data.decode("utf-8")

        self.assertIn("Lê Hoàng Phúc", html)
        self.assertIn("Chuyên viên kinh doanh", html)
        self.assertIn("Nhóm Bán Lẻ Khu Vực Miền Bắc", html)
        self.assertIn("badge-sales-rep", html)

        # Thử nghiệm chuyển sang Trưởng nhóm Trần Thị Mai Phương
        with self.client.session_transaction() as sess:
            sess["current_username"] = "team_lead"

        response2 = self.client.get("/dashboard")
        html2 = response2.data.decode("utf-8")

        self.assertIn("Trần Thị Mai Phương", html2)
        self.assertIn("Trưởng nhóm kinh doanh", html2)
        self.assertIn("Nhóm Khách Hàng Doanh Nghiệp (B2B)", html2)
        self.assertIn("badge-team-lead", html2)

    # =========================================================================
    # NHÓM 3: BẢO VỆ CHẶT CHẼ Ở BACKEND (CHẶN 403 KHI CỐ TÌNH TRUY CẬP TRÁI PHÉP)
    # =========================================================================
    def test_backend_route_protection_returns_403_for_unauthorized_user(self):
        """
        Ca 6: Nếu người dùng cố tình gõ trực tiếp URL ngoài quyền hạn,
        Backend từ chối truy cập và trả về HTTP 403 Forbidden kèm giao diện cảnh báo.
        """
        with self.client.session_transaction() as sess:
            sess["current_username"] = "sales_rep" # Chuyên viên không có quyền settings

        response = self.client.get("/settings")
        # 1. Mã trạng thái chuẩn HTTP 403
        self.assertEqual(response.status_code, 403)
        html = response.data.decode("utf-8")

        # 2. Không bị trang trắng, dùng chung layout
        self.assertIn("Enterprise Hub", html)
        self.assertIn("app-sidebar", html)

        # 3. Thông báo rõ lý do và quyền còn thiếu
        self.assertIn("Bạn Không Có Quyền Truy Cập Chức Năng Này!", html)
        self.assertIn("system_settings", html)
        self.assertIn("Lê Hoàng Phúc", html)

        # 4. Có nút gợi ý đổi sang tài khoản Giám Đốc
        self.assertIn("Đổi sang tài khoản Giám Đốc", html)

    # =========================================================================
    # NHÓM 4: KIỂM THỬ TIÊU CHÍ 3 - TƯƠNG THÍCH MÀN HÌNH 360PX
    # =========================================================================
    def test_mobile_360px_navigation_elements(self):
        """
        Ca 7: Kiểm tra cấu trúc HTML hỗ trợ đầy đủ các thành phần điều hướng trên 360px:
        - Nút Hamburger mở menu (touch target chuẩn)
        - Nút đóng Drawer cảm ứng
        - Lớp phủ nền mờ (Backdrop overlay)
        - Viewport meta tag chuẩn responsive di động
        """
        response = self.client.get("/dashboard")
        html = response.data.decode("utf-8")

        # 1. Viewport tag
        self.assertIn('name="viewport"', html)
        self.assertIn('width=device-width', html)

        # 2. Nút Hamburger trên Topbar mobile
        self.assertIn('id="hamburger-btn"', html)
        self.assertIn('class="hamburger-btn"', html)

        # 3. Nút đóng Drawer
        self.assertIn('id="close-drawer-btn"', html)
        self.assertIn('class="drawer-close-btn"', html)

        # 4. Lớp nền mờ backdrop
        self.assertIn('id="drawer-backdrop"', html)
        self.assertIn('class="drawer-backdrop"', html)

        # 5. Nút bật giả lập 360px
        self.assertIn('id="toggle-sim-btn"', html)

    def test_api_menu_endpoint_returns_json(self):
        """
        Ca 8: Kiểm tra API /api/menu trả về cấu trúc JSON chính xác cho từng vai trò.
        """
        with self.client.session_transaction() as sess:
            sess["current_username"] = "intern"

        response = self.client.get("/api/menu")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertEqual(data["user"]["username"], "intern")
        self.assertEqual(data["user"]["name"], "Phạm Minh Khôi")
        self.assertEqual(data["user"]["business_group"], "Nhóm Phát Triển Khách Hàng Mới")
        self.assertEqual(data["menu_items_count"], 1)
        self.assertEqual(data["menu_items"][0]["id"], "dashboard")

if __name__ == "__main__":
    unittest.main()
