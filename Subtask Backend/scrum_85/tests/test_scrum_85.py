"""
BỘ KIỂM THỬ TỰ ĐỘNG CHO TICKET SCRUM-85
========================================
Mã Nhiệm Vụ: SCRUM-83 / SCRUM-85
User Story:
  "Là Giám đốc kinh doanh, tôi muốn khai báo cơ cấu tổ chức kinh doanh,
   để phạm vi dữ liệu của trưởng nhóm bám đúng cây tổ chức thật."

Kiểm thử toàn diện 100% 4 Tiêu chí chấp nhận:
  1. Cấu trúc cây nhóm kinh doanh & Mỗi nhóm có 1 trưởng nhóm.
  2. Ràng buộc: Mỗi nhân viên thuộc đúng một nhóm tại một thời điểm.
  3. Cây tổ chức quyết định phạm vi dữ liệu nhìn thấy của Trưởng nhóm (Subtree scope).
  4. Khai báo khu vực địa lý và gán khu vực cho nhóm kinh doanh.
========================================
"""

import unittest
import sys
import os

# Thêm thư mục hiện tại vào sys.path để import database
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import (
    reset_database,
    get_all_teams,
    get_team,
    create_team,
    update_team,
    delete_team,
    is_circular_dependency,
    get_sub_tree_team_ids,
    get_visible_deals_for_user,
    get_all_employees,
    get_employee,
    assign_employee_to_team,
    add_employee,
    get_all_regions,
    get_region,
    create_region,
    update_region,
    delete_region,
    get_team_summary_metrics,
    DB_TEAMS,
    DB_EMPLOYEES,
    DB_REGIONS,
    DB_DEALS
)


class TestScrum85BusinessOrgTree(unittest.TestCase):

    def setUp(self):
        """Khôi phục cơ sở dữ liệu mẫu chuẩn trước mỗi ca kiểm thử."""
        reset_database()

    # ==========================================================================
    # TIÊU CHÍ 1: CẤU TRÚC CÂY NHÓM KINH DOANH & MỖI NHÓM CÓ MỘT TRƯỞNG NHÓM
    # ==========================================================================

    def test_01_team_has_tree_structure_and_unique_leader(self):
        """Xác minh các nhóm kinh doanh có quan hệ phân cấp cây và mỗi nhóm có đúng 1 trưởng nhóm."""
        teams = get_all_teams()
        self.assertGreater(len(teams), 0)

        # Kiểm tra node gốc HQ
        hq = get_team("TEAM_HQ")
        self.assertIsNotNone(hq)
        self.assertIsNone(hq["parent_id"])
        self.assertEqual(hq["leader_id"], "EMP001")
        self.assertEqual(hq["leader_name"], "Trần Hải Đăng")

        # Kiểm tra nhóm con Miền Bắc trực thuộc HQ
        north = get_team("TEAM_NORTH")
        self.assertEqual(north["parent_id"], "TEAM_HQ")
        self.assertEqual(north["leader_id"], "EMP002")

        # Kiểm tra nhóm cháu: Đội Bán lẻ Hà Nội trực thuộc Miền Bắc
        hn_retail = get_team("TEAM_HN_RETAIL")
        self.assertEqual(hn_retail["parent_id"], "TEAM_NORTH")
        self.assertEqual(hn_retail["leader_id"], "EMP004")

        # Đảm bảo mỗi nhóm đều có đúng một trưởng nhóm hợp lệ
        for t in teams:
            self.assertTrue(t["leader_id"] in DB_EMPLOYEES, f"Nhóm {t['id']} thiếu trưởng nhóm hợp lệ")

    def test_02_prevent_circular_dependency_in_team_hierarchy(self):
        """Xác minh hệ thống ngăn chặn triệt để chu trình lặp (circular loop) trong cây tổ chức."""
        # Thử gán nhóm cha của TEAM_NORTH là chính nó -> Phải bị chặn
        self.assertTrue(is_circular_dependency("TEAM_NORTH", "TEAM_NORTH"))

        # Thử gán nhóm cha của TEAM_NORTH là TEAM_HN_RETAIL (vốn là nhóm con của TEAM_NORTH) -> Phải bị chặn
        self.assertTrue(is_circular_dependency("TEAM_NORTH", "TEAM_HN_RETAIL"))

        # Kiểm tra qua hàm update_team
        success, msg = update_team(
            team_id="TEAM_NORTH",
            name="Chi Nhánh Miền Bắc",
            parent_id="TEAM_HN_RETAIL", # Thử tạo chu trình
            leader_id="EMP002",
            region_id="REG_MB"
        )
        self.assertFalse(success)
        self.assertIn("Lỗi chu trình", msg)

    def test_03_create_new_subteam_successfully(self):
        """Xác minh có thể khai báo một nhóm con mới vào cây tổ chức với trưởng nhóm và khu vực."""
        success, msg = create_team(
            team_id="TEAM_HN_VIP",
            name="Đội Khách Hàng VIP Hà Nội",
            parent_id="TEAM_NORTH",
            leader_id="EMP007",
            region_id="REG_MB",
            description="Chuyên chăm sóc khách hàng VIP khu vực Hà Nội"
        )
        self.assertTrue(success, msg)
        new_team = get_team("TEAM_HN_VIP")
        self.assertIsNotNone(new_team)
        self.assertEqual(new_team["parent_id"], "TEAM_NORTH")
        self.assertEqual(new_team["leader_id"], "EMP007")
        self.assertEqual(new_team["region_id"], "REG_MB")

    # ==========================================================================
    # TIÊU CHÍ 2: MỖI NHÂN VIÊN THUỘC ĐÚNG MỘT NHÓM TẠI MỘT THỜI ĐIỂM
    # ==========================================================================

    def test_04_employee_belongs_to_exactly_one_team(self):
        """Xác minh tại mọi thời điểm, mỗi nhân viên chỉ thuộc duy nhất một nhóm kinh doanh."""
        employees = get_all_employees()
        for emp in employees:
            team_id = emp.get("team_id")
            self.assertIsNotNone(team_id)
            self.assertIn(team_id, DB_TEAMS, f"Nhân viên {emp['id']} thuộc nhóm không tồn tại")

    def test_05_transferring_employee_updates_team_exclusively(self):
        """Xác minh khi điều chuyển nhân viên sang nhóm mới, nhân viên rời khỏi nhóm cũ ngay lập tức."""
        emp_id = "EMP007" # Ban đầu thuộc TEAM_HN_RETAIL
        emp_before = get_employee(emp_id)
        self.assertEqual(emp_before["team_id"], "TEAM_HN_RETAIL")

        # Điều chuyển sang TEAM_HN_CORP
        success, msg = assign_employee_to_team(emp_id, "TEAM_HN_CORP")
        self.assertTrue(success)

        emp_after = get_employee(emp_id)
        self.assertEqual(emp_after["team_id"], "TEAM_HN_CORP")

        # Xác minh trong danh sách thành viên của TEAM_HN_RETAIL không còn nhân viên này
        retail_members = [e["id"] for e in DB_EMPLOYEES.values() if e["team_id"] == "TEAM_HN_RETAIL"]
        corp_members = [e["id"] for e in DB_EMPLOYEES.values() if e["team_id"] == "TEAM_HN_CORP"]

        self.assertNotIn(emp_id, retail_members)
        self.assertIn(emp_id, corp_members)

    # ==========================================================================
    # TIÊU CHÍ 3: CÂY TỔ CHỨC QUYẾT ĐỊNH PHẠM VI DỮ LIỆU CỦA TRƯỞNG NHÓM (SUBTREE)
    # ==========================================================================

    def test_06_subtree_traversal_accuracy(self):
        """Xác minh thuật toán tìm tập hợp tất cả nhóm con cháu (subtree) chính xác."""
        # Subtree của HQ: Gồm tất cả các nhóm (HQ, NORTH, SOUTH, HN_RETAIL, HN_CORP, SG_TEAM1)
        hq_subtree = get_sub_tree_team_ids("TEAM_HQ")
        self.assertEqual(len(hq_subtree), 6)
        self.assertTrue({"TEAM_HQ", "TEAM_NORTH", "TEAM_SOUTH", "TEAM_HN_RETAIL", "TEAM_HN_CORP", "TEAM_SG_TEAM1"}.issubset(hq_subtree))

        # Subtree của Chi nhánh Miền Bắc: Gồm NORTH, HN_RETAIL, HN_CORP
        north_subtree = get_sub_tree_team_ids("TEAM_NORTH")
        self.assertEqual(north_subtree, {"TEAM_NORTH", "TEAM_HN_RETAIL", "TEAM_HN_CORP"})

        # Subtree của Đội Bán lẻ Hà Nội: Chỉ có chính nó (lá cây - leaf node)
        retail_subtree = get_sub_tree_team_ids("TEAM_HN_RETAIL")
        self.assertEqual(retail_subtree, {"TEAM_HN_RETAIL"})

    def test_07_sales_director_sees_all_deals_nationwide(self):
        """Xác minh Giám đốc kinh doanh (Node gốc) nhìn thấy 100% dữ liệu toàn quốc."""
        director_emp_id = "EMP001" # Trần Hải Đăng - GĐKD
        deals, meta = get_visible_deals_for_user(director_emp_id)

        self.assertEqual(meta["scope_type"], "DIRECTOR_ALL")
        self.assertEqual(len(deals), len(DB_DEALS))
        # Có dữ liệu của cả Bắc, Nam và HQ
        deal_teams = {d["team_id"] for d in deals}
        self.assertIn("TEAM_HQ", deal_teams)
        self.assertIn("TEAM_HN_CORP", deal_teams)
        self.assertIn("TEAM_SG_TEAM1", deal_teams)

    def test_08_branch_leader_sees_only_own_subtree_and_not_peer_branch(self):
        """
        Xác minh Trưởng Chi nhánh Miền Bắc (EMP002):
        - Nhìn thấy dữ liệu của nhóm mình + tất cả nhóm con thuộc Miền Bắc (HN Retail, HN Corp).
        - TUYỆT ĐỐI KHÔNG nhìn thấy dữ liệu của Chi nhánh Miền Nam (SG_TEAM1) hay HQ.
        """
        north_leader_id = "EMP002" # Nguyễn Minh Tuấn
        deals, meta = get_visible_deals_for_user(north_leader_id)

        self.assertEqual(meta["scope_type"], "TEAM_LEADER_SUBTREE")
        deal_teams = {d["team_id"] for d in deals}

        # Phải nhìn thấy dữ liệu thuộc Miền Bắc
        self.assertTrue(deal_teams.issubset({"TEAM_NORTH", "TEAM_HN_RETAIL", "TEAM_HN_CORP"}))
        # Không được chứa deal của Miền Nam
        self.assertNotIn("TEAM_SG_TEAM1", deal_teams)
        self.assertNotIn("TEAM_SOUTH", deal_teams)
        # Không được chứa deal của HQ
        self.assertNotIn("TEAM_HQ", deal_teams)

    def test_09_sub_team_leader_sees_only_own_team(self):
        """Xác minh Trưởng nhóm cấp 2 (HN Retail - EMP004) chỉ nhìn thấy dữ liệu của đội mình."""
        hn_retail_leader = "EMP004" # Phạm Quốc Dũng
        deals, meta = get_visible_deals_for_user(hn_retail_leader)

        self.assertEqual(meta["scope_type"], "TEAM_LEADER_SUBTREE")
        for d in deals:
            self.assertEqual(d["team_id"], "TEAM_HN_RETAIL")

    def test_10_individual_sales_rep_sees_only_assigned_deals(self):
        """Xác minh Nhân viên kinh doanh thông thường (EMP007 - Vũ Anh Tú) chỉ nhìn thấy deal do mình phụ trách."""
        rep_emp_id = "EMP007"
        deals, meta = get_visible_deals_for_user(rep_emp_id)

        self.assertEqual(meta["scope_type"], "INDIVIDUAL_REP")
        for d in deals:
            self.assertEqual(d["assignee_id"], rep_emp_id)

    # ==========================================================================
    # TIÊU CHÍ 4: KHAI BÁO KHU VỰC ĐỊA LÝ VÀ GÁN KHU VỰC CHO NHÓM
    # ==========================================================================

    def test_11_create_and_manage_geographic_regions(self):
        """Xác minh tính năng khai báo và quản lý khu vực địa lý."""
        success, msg = create_region(
            region_id="REG_TAY_NGUYEN",
            name="Vùng Tây Nguyên",
            code="TN",
            provinces="Đắk Lắk, Gia Lai, Lâm Đồng, Kon Tum, Đắk Nông",
            description="Thị trường nông sản và cà phê xuất khẩu",
            badge_color="#854d0e"
        )
        self.assertTrue(success, msg)

        # Lấy thông tin khu vực vừa tạo
        region = get_region("REG_TAY_NGUYEN")
        self.assertIsNotNone(region)
        self.assertEqual(region["code"], "TN")
        self.assertIn("Đắk Lắk", region["provinces"])

    def test_12_assign_region_to_team(self):
        """Xác minh có thể gán khu vực địa lý cho nhóm kinh doanh."""
        # Tạo khu vực mới
        create_region("REG_DBSCL", "Đồng Bằng Sông Cửu Long", "Mekong", "Cần Thơ, Tiền Giang, An Giang")
        
        # Gán khu vực cho TEAM_SG_TEAM1
        success, msg = update_team(
            team_id="TEAM_SG_TEAM1",
            name="Đội Kinh Doanh Trung Tâm TP.HCM",
            parent_id="TEAM_SOUTH",
            leader_id="EMP006",
            region_id="REG_DBSCL",
            description="Phụ trách mở rộng thị trường miền Tây"
        )
        self.assertTrue(success, msg)

        team = get_team("TEAM_SG_TEAM1")
        self.assertEqual(team["region_id"], "REG_DBSCL")
        self.assertEqual(team["region_name"], "Đồng Bằng Sông Cửu Long")

    def test_13_prevent_deleting_region_in_use(self):
        """Xác minh không thể xóa khu vực địa lý nếu đang có nhóm kinh doanh phụ trách."""
        # REG_MB đang được gán cho TEAM_NORTH, TEAM_HN_RETAIL, TEAM_HN_CORP
        success, msg = delete_region("REG_MB")
        self.assertFalse(success)
        self.assertIn("Không thể xóa khu vực", msg)


if __name__ == "__main__":
    unittest.main()
