"""
Kiểm thử Tiêu chí 3 (Acceptance Criteria 3) - Ticket SCRUM-56:
"Lưu và đặt tên cho bộ lọc hay dùng"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database, TEMP_HOT


class TestAC3SavedFilters(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_default_system_saved_filters_exist(self):
        """
        Chứng minh hệ thống cài sẵn các bộ lọc thông minh cho buổi sáng:
        1. ☀️ Cần gọi sáng nay (Mặc định)
        2. 🚩 Báo động: Quá hạn SLA
        3. 🔥 Lead nóng của tôi
        """
        saved = self.db.get_saved_filters()
        self.assertGreaterEqual(len(saved), 3)

        # Kiểm tra có bộ lọc mặc định buổi sáng
        default_filter = next((f for f in saved if f.get("is_default")), None)
        self.assertIsNotNone(default_filter)
        self.assertIn("Cần Gọi Sáng Nay", default_filter["name"])

    def test_save_new_custom_named_filter(self):
        """
        Chứng minh nhân viên kinh doanh có thể:
        1. Đặt tên tùy thích cho bộ lọc hay dùng (VD: '🔥 Khách Hàng VIP Google Của Tuấn')
        2. Lưu tổ hợp tiêu chí tìm kiếm
        3. Bộ lọc mới xuất hiện trong danh sách saved filters
        """
        filter_name = "🔥 Khách Hàng VIP Google Của Tuấn"
        criteria = {
            "source": "Google Ads",
            "temperature": TEMP_HOT,
            "assigned_to": "mine"
        }

        new_filter = self.db.save_filter(
            name=filter_name,
            criteria=criteria,
            user_id="usr-01",
            icon="💎",
            is_default=False
        )

        self.assertIsNotNone(new_filter["id"])
        self.assertEqual(new_filter["name"], filter_name)
        self.assertEqual(new_filter["icon"], "💎")
        self.assertEqual(new_filter["criteria"], criteria)

        # Kiểm tra tồn tại trong DB
        all_saved = self.db.get_saved_filters(user_id="usr-01")
        found = any(f["id"] == new_filter["id"] for f in all_saved)
        self.assertTrue(found)

    def test_execute_saved_filter_produces_consistent_results(self):
        """
        Chứng minh khi áp dụng bộ lọc đã lưu:
        Kết quả lọc trả về chính xác theo đúng các tiêu chí đã lưu trước đó.
        """
        new_filter = self.db.save_filter(
            name="Test Bộ Lọc Nóng Google",
            criteria={"source": "Google Ads", "temperature": TEMP_HOT},
            user_id="usr-01"
        )

        # Thực thi lọc bằng criteria của bộ lọc đã lưu
        leads = self.db.filter_leads(new_filter["criteria"], user_id="usr-01")
        self.assertGreater(len(leads), 0)
        for l in leads:
            self.assertEqual(l["source"], "Google Ads")
            self.assertEqual(l["temperature"], TEMP_HOT)

    def test_delete_saved_filter(self):
        """Chứng minh có thể xóa bộ lọc đã lưu khi không còn nhu cầu"""
        new_filter = self.db.save_filter(
            name="Bộ lọc tạm thời",
            criteria={"temperature": TEMP_HOT},
            user_id="usr-01"
        )
        fid = new_filter["id"]

        success = self.db.delete_filter(fid)
        self.assertTrue(success)
        self.assertNotIn(fid, self.db.saved_filters)

    def test_set_filter_as_default(self):
        """Chứng minh có thể chọn một bộ lọc bất kỳ làm mặc định khi mở máy"""
        custom_filter = self.db.save_filter(
            name="Bộ lọc mở máy mới",
            criteria={"assigned_to": "mine"},
            user_id="usr-01",
            is_default=True
        )

        self.assertTrue(custom_filter["is_default"])
        # Các bộ lọc khác không còn là mặc định
        for fid, f in self.db.saved_filters.items():
            if fid != custom_filter["id"]:
                self.assertFalse(f["is_default"])


if __name__ == "__main__":
    unittest.main()
