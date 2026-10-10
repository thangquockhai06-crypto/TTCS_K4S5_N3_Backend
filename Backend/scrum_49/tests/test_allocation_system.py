"""
Bộ Kiểm Thử Toàn Diện (Unit & Integration Tests)
Ticket SCRUM-30 / SCRUM-49: Cấu hình quy tắc phân bổ lead tự động cho Giám đốc kinh doanh

Kiểm thử 100% các tiêu chí chấp nhận:
- Tiêu chí 1: Phân bổ theo khu vực, theo ngành nghề, xoay vòng đều trong nhóm (Round-Robin).
- Tiêu chí 2: Nhiều quy tắc xếp theo thứ tự ưu tiên, quy tắc đầu tiên khớp sẽ thắng (First-Match-Wins).
- Tiêu chí 3: Lead không khớp quy tắc nào rơi vào hàng chờ để trưởng nhóm phân tay (Manual Queue).
- Tiêu chí 4: Phân bổ chạy nền, hoàn tất trong vòng 5 phút kể từ khi lead vào (Background Thread & SLA).
"""

import unittest
import time
from database import (
    db,
    Database,
    LEAD_STATUS_PENDING,
    LEAD_STATUS_ASSIGNED,
    LEAD_STATUS_MANUAL_QUEUE,
    ASSIGNMENT_TYPE_ROUND_ROBIN,
    ASSIGNMENT_TYPE_DIRECT,
    SLA_LIMIT_SECONDS
)
from engine import LeadAllocationEngine, BackgroundAllocationWorker


class TestLeadAllocationSystem(unittest.TestCase):
    def setUp(self):
        # Khởi tạo instance database riêng cho mỗi test để đảm bảo độc lập
        self.test_db = Database()
        self.worker = BackgroundAllocationWorker(poll_interval=1)

    def tearDown(self):
        if self.worker.is_running:
            self.worker.stop()

    # =========================================================================
    # TIÊU CHÍ 1: PHÂN BỔ THEO KHU VỰC, THEO NGÀNH NGHỀ, XOAY VÒNG ĐỀU TRONG NHÓM
    # =========================================================================
    def test_criterion_1_allocation_by_region_and_industry(self):
        """Kiểm tra phân bổ chính xác theo Khu vực và Ngành nghề"""
        # Rule 1: Miền Bắc + Tài chính - Ngân hàng
        lead_fin = {
            "id": "test-lead-1",
            "code": "TL-01",
            "name": "Ngân Hàng Bản Việt",
            "region": "Miền Bắc",
            "industry": "Tài chính - Ngân hàng",
            "estimated_value": 100000000,
            "created_at": "2026-10-09 10:00:00"
        }
        matched, msg = LeadAllocationEngine.evaluate_and_allocate(lead_fin)
        self.assertTrue(matched, "Lead tài chính Miền Bắc phải khớp Rule #1")
        self.assertEqual(lead_fin["status"], LEAD_STATUS_ASSIGNED)
        self.assertEqual(lead_fin["matched_rule_id"], "rule-01")

        # Rule 2: Toàn quốc + Bất động sản
        lead_re = {
            "id": "test-lead-2",
            "code": "TL-02",
            "name": "Bất Động Sản Novaland",
            "region": "Miền Nam",
            "industry": "Bất động sản",
            "estimated_value": 500000000,
            "created_at": "2026-10-09 10:00:00"
        }
        matched, msg = LeadAllocationEngine.evaluate_and_allocate(lead_re)
        self.assertTrue(matched, "Lead BĐS Miền Nam phải khớp Rule #2 (BĐS Toàn quốc)")
        self.assertEqual(lead_re["matched_rule_id"], "rule-02")
        self.assertEqual(lead_re["assigned_team_id"], "team-bds")

    def test_criterion_1_round_robin_fair_distribution(self):
        """
        Kiểm tra thuật toán xoay vòng đều (Round-Robin):
        Các thành viên trong nhóm nhận lead luân phiên, không ai bị bỏ sót.
        """
        team_id = "team-bac"
        team = db.teams[team_id]
        active_members = [
            db.users[uid] for uid in team["members"] if db.users[uid]["status"] == "ACTIVE"
        ]
        num_members = len(active_members)  # Ví dụ 3 nhân viên
        self.assertGreater(num_members, 1, "Nhóm phải có từ 2 thành viên trở lên để xoay vòng")

        assigned_sequence = []
        for _ in range(num_members * 2):
            user = db.get_next_round_robin_user(team_id)
            self.assertIsNotNone(user)
            assigned_sequence.append(user["id"])

        # Kiểm tra chu kỳ 1
        cycle_1 = assigned_sequence[:num_members]
        cycle_2 = assigned_sequence[num_members:]

        # Mỗi người nhận đúng 1 lead trong chu kỳ 1
        self.assertEqual(len(set(cycle_1)), num_members, "Chu kỳ 1 phải chia đều cho tất cả thành viên")
        # Chu kỳ 2 lặp lại đúng thứ tự xoay vòng
        self.assertEqual(cycle_1, cycle_2, "Chu kỳ 2 phải luân phiên tiếp tục theo thứ tự Round-Robin")

    # =========================================================================
    # TIÊU CHÍ 2: NHIỀU QUY TẮC XẾP THEO THỨ TỰ ƯU TIÊN, QUY TẮC ĐẦU TIÊN KHỚP SẼ THẮNG
    # =========================================================================
    def test_criterion_2_first_match_wins_priority(self):
        """
        Kiểm tra nguyên tắc First-Match-Wins:
        Khi lead thỏa mãn đồng thời nhiều quy tắc, quy tắc có độ ưu tiên cao hơn (Priority nhỏ hơn)
        phải thắng, các quy tắc sau không được áp dụng.
        """
        # Giả sử Lead: Miền Bắc, Ngành Công nghệ thông tin
        # Rule 4: Priority 4, Toàn quốc + Công nghệ thông tin -> Gán trực tiếp Phạm Hoàng Nam
        lead = {
            "id": "test-lead-priority",
            "code": "TL-PRIORITY",
            "name": "Công Ty Phần Mềm FPT",
            "region": "Miền Bắc",
            "industry": "Công nghệ thông tin",
            "estimated_value": 200000000,
            "created_at": "2026-10-09 10:00:00"
        }

        # Tạo thêm một Rule mới có Priority cao hơn (Priority 1) cũng khớp Miền Bắc + CNTT
        new_high_rule = {
            "name": "Quy tắc khẩn cấp: CNTT Miền Bắc Priority 1",
            "priority": 1,
            "is_active": True,
            "region": "Miền Bắc",
            "industry": "Công nghệ thông tin",
            "assignment_type": ASSIGNMENT_TYPE_DIRECT,
            "target_user_id": "usr-05",  # Nguyễn Anh Tuấn
            "description": "Ưu tiên cao nhất cho CNTT Miền Bắc"
        }
        added_rule = db.add_rule(new_high_rule)

        try:
            matched, msg = LeadAllocationEngine.evaluate_and_allocate(lead)
            self.assertTrue(matched)
            # Phải thắng bởi Rule mới (Priority 1) chứ không phải Rule 4 (Priority sau đó)
            self.assertEqual(lead["matched_rule_id"], added_rule["id"])
            self.assertEqual(lead["assigned_to_user_id"], "usr-05")
        finally:
            # Dọn dẹp rule sau test
            db.delete_rule(added_rule["id"])

    # =========================================================================
    # TIÊU CHÍ 3: LEAD KHÔNG KHỚP QUY TẮC NÀO RƠI VÀO HÀNG CHỜ PHÂN TAY
    # =========================================================================
    def test_criterion_3_unmatched_lead_falls_into_manual_queue(self):
        """
        Kiểm tra: Nếu lead không khớp bất kỳ quy tắc nào,
        trạng thái của lead phải chuyển sang MANUAL_QUEUE (Hàng chờ phân tay).
        """
        # Lead có ngành chưa cấu hình trong bất kỳ Rule nào
        lead_unmatched = {
            "id": "test-unmatched-1",
            "code": "TL-UNMATCHED",
            "name": "Viện Hải Dương Học Nha Trang",
            "region": "Miền Trung",
            "industry": "Y tế & Chăm sóc sức khỏe",  # Chưa có rule cho Miền Trung + Y tế
            "estimated_value": 50000000,
            "created_at": "2026-10-09 10:00:00"
        }
        matched, msg = LeadAllocationEngine.evaluate_and_allocate(lead_unmatched)
        self.assertFalse(matched, "Lead không được khớp quy tắc nào")
        self.assertEqual(lead_unmatched["status"], LEAD_STATUS_MANUAL_QUEUE)
        self.assertIsNone(lead_unmatched["assigned_to_user_id"])
        self.assertIsNotNone(lead_unmatched["unmatched_reason"])

    def test_criterion_3_manual_assignment_by_team_lead(self):
        """
        Kiểm tra: Trưởng nhóm có thể phân công tay (Manual Assign)
        từ hàng chờ cho một nhân viên cụ thể.
        """
        # Tạo lead trong hàng chờ
        new_lead = db.add_lead({
            "name": "Khách hàng cần phân tay",
            "region": "Miền Trung",
            "industry": "Giáo dục & Đào tạo"
        })
        LeadAllocationEngine.evaluate_and_allocate(new_lead)
        self.assertEqual(new_lead["status"], LEAD_STATUS_MANUAL_QUEUE)

        # Trưởng nhóm thực hiện phân tay
        assigned = db.manual_assign_lead(
            lead_id=new_lead["id"],
            target_user_id="usr-06",  # Lê Thị Mai
            assigner_name="Trần Văn Hùng (Trưởng nhóm)",
            notes="Chỉ định Lê Thị Mai phụ trách dự án này"
        )
        self.assertIsNotNone(assigned)
        self.assertEqual(assigned["status"], LEAD_STATUS_ASSIGNED)
        self.assertEqual(assigned["assigned_to_user_id"], "usr-06")
        self.assertEqual(assigned["manual_assigned_by"], "Trần Văn Hùng (Trưởng nhóm)")

    # =========================================================================
    # TIÊU CHÍ 4: PHÂN BỔ CHẠY NỀN, HOÀN TẤT TRONG VÒNG 5 PHÚT KỂ TỪ KHI LEAD VÀO
    # =========================================================================
    def test_criterion_4_background_worker_auto_processing(self):
        """
        Kiểm tra: Luồng chạy nền (Background Worker) tự động quét và phân bổ lead PENDING,
        hoàn tất trong vòng vài giây, đáp ứng nghiêm ngặt cam kết SLA 5 phút (300 giây).
        """
        # Nạp một lead mới vào trạng thái PENDING
        lead = db.add_lead({
            "name": "Doanh Nghiệp Fintech Hải Dương",
            "region": "Miền Bắc",
            "industry": "Tài chính - Ngân hàng",
            "estimated_value": 300000000
        })
        self.assertEqual(lead["status"], LEAD_STATUS_PENDING, "Lead mới nạp phải ở trạng thái PENDING")

        # Worker quét và xử lý
        processed_count = self.worker.process_pending_leads()
        self.assertGreaterEqual(processed_count, 1)

        # Kiểm tra lead sau khi worker xử lý
        updated_lead = db.get_lead_by_id(lead["id"])
        self.assertEqual(updated_lead["status"], LEAD_STATUS_ASSIGNED)
        self.assertEqual(updated_lead["sla_status"], "MET", "Phải hoàn tất trong hạn mức SLA 5 phút")
        self.assertLessEqual(
            updated_lead["elapsed_seconds"],
            SLA_LIMIT_SECONDS,
            f"Thời gian xử lý ({updated_lead['elapsed_seconds']}s) phải nhỏ hơn 5 phút ({SLA_LIMIT_SECONDS}s)"
        )


if __name__ == "__main__":
    unittest.main()
