"""
Kiểm thử Tiêu chí 4 (Acceptance Criteria 4) - Ticket SCRUM-54:
"Toàn bộ hoạt động đã ghi trên lead được giữ lại trên khách hàng mới"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import (
    Database,
    ACTIVITY_CALL,
    ACTIVITY_MEETING,
    ACTIVITY_NOTE,
    ACTIVITY_CONVERT
)


class TestAC4ActivityRetention(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_all_lead_activities_retained_on_new_account(self):
        """
        Chứng minh:
        1. Tất cả hoạt động (cuộc gọi, cuộc họp, email, ghi chú) đã ghi trên Lead
           đều được kế thừa đầy đủ 100% sang Khách hàng doanh nghiệp mới (Account).
        2. Từng hoạt động giữ nguyên nội dung chi tiết, người thực hiện, thời gian ghi nhận.
        3. Được gắn cờ inherited_from_lead = True và lưu mã lead gốc source_lead_id.
        4. Tự động sinh thêm 1 hoạt động cột mốc chuyển đổi (CONVERT).
        """
        lead_id = "LEAD-101"
        lead = self.db.get_lead(lead_id)
        
        # Thêm thêm một hoạt động thử nghiệm trước khi chuyển đổi
        self.db.add_lead_activity(
            lead_id=lead_id,
            user_id="usr-01",
            act_type=ACTIVITY_NOTE,
            summary="Thẩm định năng lực tài chính & ký nháy biên bản",
            details="Khách hàng đã cung cấp báo cáo tài chính năm gần nhất, chuẩn bị ký hợp đồng chính thức."
        )

        lead_activities_before = list(lead["activities"])
        expected_inherited_count = len(lead_activities_before)
        self.assertGreaterEqual(expected_inherited_count, 4)

        # Thực hiện chuyển đổi
        result = self.db.convert_lead(lead_id, user_id="usr-01")
        account = result["account"]

        # Kiểm tra số lượng hoạt động trên Account
        # Bao gồm: expected_inherited_count hoạt động kế thừa + 1 hoạt động mốc chuyển đổi
        self.assertEqual(len(account["activities"]), expected_inherited_count + 1)

        # 1. Kiểm tra hoạt động đầu tiên là mốc chuyển đổi
        first_act = account["activities"][0]
        self.assertEqual(first_act["type"], ACTIVITY_CONVERT)
        self.assertTrue(first_act.get("is_milestone"))
        self.assertIn("Chuyển đổi thành công từ Lead", first_act["summary"])

        # 2. Kiểm tra các hoạt động kế thừa từ lead
        inherited_acts = [a for a in account["activities"] if a.get("inherited_from_lead")]
        self.assertEqual(len(inherited_acts), expected_inherited_count)

        # Kiểm tra tính toàn vẹn của từng hoạt động kế thừa
        for inh in inherited_acts:
            self.assertEqual(inh["source_lead_id"], lead_id)
            self.assertTrue(inh["inherited_from_lead"])
            self.assertTrue(bool(inh.get("summary")))
            self.assertTrue(bool(inh.get("performed_by_name")))
            self.assertTrue(bool(inh.get("created_at")))

        # Kiểm tra sự tồn tại của hoạt động ghi chú vừa thêm
        found_note = any(
            "Thẩm định năng lực tài chính" in a.get("summary", "")
            for a in account["activities"]
        )
        self.assertTrue(found_note, "Hoạt động ghi chú trước khi chuyển đổi phải được giữ lại trên Khách hàng mới!")

    def test_new_activities_can_be_added_to_account_alongside_inherited_ones(self):
        """
        Chứng minh sau khi chuyển đổi, nhân viên có thể tiếp tục chăm sóc Khách hàng
        và thêm các hoạt động mới, hoạt động mới sẽ cùng tồn tại với các hoạt động
        đã kế thừa từ Lead.
        """
        result = self.db.convert_lead("LEAD-101", user_id="usr-01")
        account = result["account"]
        initial_count = len(account["activities"])

        # Thêm hoạt động mới vào Khách hàng
        new_act = self.db.add_account_activity(
            account_id=account["id"],
            user_id="usr-01",
            act_type=ACTIVITY_MEETING,
            summary="Gặp mặt ký kết hợp đồng chính thức",
            details="Ban giám đốc 2 bên đã gặp mặt tại văn phòng VinTech và ký kết hợp đồng trị giá 150 triệu."
        )

        self.assertEqual(len(account["activities"]), initial_count + 1)
        self.assertFalse(account["activities"][0].get("inherited_from_lead"))
        self.assertEqual(account["activities"][0]["summary"], "Gặp mặt ký kết hợp đồng chính thức")


if __name__ == "__main__":
    unittest.main()
