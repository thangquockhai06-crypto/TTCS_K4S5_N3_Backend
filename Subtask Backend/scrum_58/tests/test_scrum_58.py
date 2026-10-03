"""
BỘ KIỂM THỬ TỰ ĐỘNG TOÀN DIỆN CHO TICKET SCRUM-58
==================================================
Mã Nhiệm Vụ: SCRUM-50 / SCRUM-58
User Story:
    "Là Nhân viên kinh doanh, tôi muốn quản lý người liên hệ và vai trò của họ
     trong quyết định mua, để biết phải thuyết phục ai và ai là người có thể cản thương vụ."

Kiểm tra 100% 4 Tiêu chí chấp nhận (Acceptance Criteria):
    - Tiêu chí 1: Mỗi khách hàng có nhiều người liên hệ; mỗi người có chức danh, email, SĐT.
    - Tiêu chí 2: Đánh dấu 4 vai trò trong quyết định mua: người quyết định, người ảnh hưởng,
                  người dùng cuối, người cản trở.
    - Tiêu chí 3: Đánh dấu một người là đầu mối chính (duy nhất 1 người tại một thời điểm).
    - Tiêu chí 4: Một người liên hệ chuyển sang công ty khác thì gắn lại được sang khách hàng mới,
                  giữ nguyên lịch sử công tác và vai trò cũ.
==================================================
"""

import unittest
import sys
import os

# Thêm thư mục hiện tại vào sys.path để import app và database
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database import (
    reset_database,
    get_all_customers,
    get_customer,
    get_all_contacts,
    get_contacts_by_customer,
    get_contact,
    add_contact,
    update_contact,
    delete_contact,
    set_primary_contact,
    transfer_contact_to_new_customer,
    get_buying_decision_matrix,
    validate_email_address,
    validate_phone_number,
    BUYING_ROLES,
    DB_CUSTOMERS,
    DB_CONTACTS
)
from app import app


class TestScrum58BuyingDecisionRoles(unittest.TestCase):
    """Bộ ca kiểm thử tự động xác thực nghiệp vụ SCRUM-58."""

    def setUp(self):
        """Khôi phục dữ liệu ban đầu trước mỗi ca test."""
        reset_database()
        self.app = app.test_client()
        self.app.testing = True

    # ==========================================================================
    # TIÊU CHÍ 1: MỖI KHÁCH HÀNG CÓ NHIỀU NGƯỜI LIÊN HỆ, CÓ CHỨC DANH, EMAIL, SĐT
    # ==========================================================================
    def test_tc1_customer_has_multiple_contacts(self):
        """Kiểm tra một khách hàng có thể sở hữu nhiều người liên hệ khác nhau."""
        contacts_c1 = get_contacts_by_customer("CUST001")
        self.assertGreaterEqual(len(contacts_c1), 3, "Khách hàng CUST001 phải có nhiều hơn hoặc bằng 3 liên hệ")
        
        # Thêm người liên hệ thứ 5 cho CUST001
        new_c = add_contact(
            customer_id="CUST001",
            full_name="Nguyễn Văn An",
            job_title="Phó Phòng Kỹ Thuật",
            email="an.nguyen@vinatech-group.vn",
            phone="0911223344",
            buying_role="influencer"
        )
        self.assertIsNotNone(new_c)
        updated_contacts = get_contacts_by_customer("CUST001")
        self.assertEqual(len(updated_contacts), len(contacts_c1) + 1)

    def test_tc1_contact_attributes_and_validations(self):
        """Kiểm tra bắt buộc phải có chức danh, email đúng định dạng và số điện thoại VN hợp lệ."""
        # 1. Hợp lệ
        contact = add_contact(
            customer_id="CUST002",
            full_name="Trần Thị Bích",
            job_title="Trưởng Ban Pháp Chế",
            email="bich.tran@globalmech.com.vn",
            phone="0988776655",
            buying_role="influencer"
        )
        self.assertEqual(contact["job_title"], "Trưởng Ban Pháp Chế")
        self.assertEqual(contact["email"], "bich.tran@globalmech.com.vn")
        self.assertEqual(contact["phone"], "0988776655")

        # 2. Thiếu chức danh -> Bắt lỗi ValueError
        with self.assertRaises(ValueError):
            add_contact(
                customer_id="CUST002",
                full_name="Lê Văn C",
                job_title="",  # Rỗng
                email="levanc@example.com",
                phone="0912345678",
                buying_role="end_user"
            )

        # 3. Email sai định dạng -> Bắt lỗi ValueError
        with self.assertRaises(ValueError):
            add_contact(
                customer_id="CUST002",
                full_name="Lê Văn D",
                job_title="Kế toán viên",
                email="email_khong_hop_le",
                phone="0912345678",
                buying_role="end_user"
            )

        # 4. Số điện thoại sai đầu số mạng VN hoặc sai độ dài -> Bắt lỗi ValueError
        with self.assertRaises(ValueError):
            add_contact(
                customer_id="CUST002",
                full_name="Lê Văn E",
                job_title="Kế toán trưởng",
                email="levane@example.com",
                phone="012345",  # Quá ngắn
                buying_role="end_user"
            )

    # ==========================================================================
    # TIÊU CHÍ 2: ĐÁNH DẤU 4 VAI TRÒ TRONG QUYẾT ĐỊNH MUA
    # ==========================================================================
    def test_tc2_buying_roles_assignment(self):
        """Kiểm tra gán đúng 4 vai trò mua: decision_maker, influencer, end_user, blocker."""
        roles = ["decision_maker", "influencer", "end_user", "blocker"]
        for role in roles:
            c = add_contact(
                customer_id="CUST003",
                full_name=f"Nhân Sự {role}",
                job_title=f"Vị trí {role}",
                email=f"test.{role}@asiaretail.com",
                phone="0901234567",
                buying_role=role
            )
            self.assertEqual(c["buying_role"], role)
            self.assertIn(role, BUYING_ROLES)

    def test_tc2_invalid_buying_role_rejected(self):
        """Kiểm tra hệ thống từ chối nếu truyền vào vai trò không hợp lệ."""
        with self.assertRaises(ValueError):
            add_contact(
                customer_id="CUST003",
                full_name="Người Thử Nghiệm",
                job_title="Tester",
                email="tester@asiaretail.com",
                phone="0901234567",
                buying_role="vai_tro_la_lung"  # Không nằm trong 4 vai trò
            )

    def test_tc2_buying_decision_matrix_power_map(self):
        """Kiểm tra phân tích Ma trận Quyết định mua hàng (Buying Decision Matrix)."""
        matrix_data = get_buying_decision_matrix("CUST001")
        matrix = matrix_data["matrix"]
        
        # CUST001 có đầy đủ các vai trò mẫu
        self.assertGreaterEqual(len(matrix["decision_makers"]), 1, "Phải có Người Quyết Định")
        self.assertGreaterEqual(len(matrix["influencers"]), 1, "Phải có Người Ảnh Hưởng")
        self.assertGreaterEqual(len(matrix["end_users"]), 1, "Phải có Người Dùng Cuối")
        self.assertGreaterEqual(len(matrix["blockers"]), 1, "Phải có Người Cản Trở")
        
        # Kiểm tra người cản trở là CONT004 (Vũ Đình Khải)
        blocker_names = [b["full_name"] for b in matrix["blockers"]]
        self.assertIn("Vũ Đình Khải", blocker_names)

    # ==========================================================================
    # TIÊU CHÍ 3: ĐÁNH DẤU MỘT NGƯỜI LÀ ĐẦU MỐI CHÍNH (PRIMARY CONTACT)
    # ==========================================================================
    def test_tc3_single_primary_contact_constraint(self):
        """
        Kiểm tra tính ràng buộc: Mỗi khách hàng chỉ có duy nhất 1 đầu mối chính.
        Khi đặt một người mới làm đầu mối chính, người cũ tự động gỡ cờ.
        """
        cust_id = "CUST001"
        # Ban đầu CONT001 (Nguyễn Hoàng Nam) là đầu mối chính
        c1 = get_contact("CONT001")
        self.assertTrue(c1["is_primary"])

        # Đặt CONT002 (Lê Thị Thanh Thảo) làm đầu mối chính mới
        success = set_primary_contact(cust_id, "CONT002")
        self.assertTrue(success)

        # Kiểm tra: CONT002 trở thành đầu mối chính
        c2 = get_contact("CONT002")
        self.assertTrue(c2["is_primary"])

        # Kiểm tra: CONT001 tự động bị gỡ cờ đầu mối chính
        c1_updated = get_contact("CONT001")
        self.assertFalse(c1_updated["is_primary"])

        # Kiểm tra toàn bộ khách hàng CUST001 chỉ có duy nhất 1 người có is_primary = True
        all_contacts = get_contacts_by_customer(cust_id)
        primaries = [c for c in all_contacts if c.get("is_primary")]
        self.assertEqual(len(primaries), 1, "Chỉ được phép có duy nhất 1 đầu mối chính trong 1 công ty")
        self.assertEqual(primaries[0]["id"], "CONT002")

    # ==========================================================================
    # TIÊU CHÍ 4: CHUYỂN SANG CÔNG TY KHÁC, GẮN SANG KHÁCH HÀNG MỚI, GIỮ NGUYÊN LỊCH SỬ
    # ==========================================================================
    def test_tc4_transfer_contact_and_preserve_history(self):
        """
        Kiểm tra chuyển người liên hệ sang khách hàng mới:
        - Gắn đúng vào khách hàng mới
        - Cập nhật chức danh mới, email mới, vai trò mua mới
        - Bảo lưu trọn vẹn toàn bộ lịch sử công tác tại công ty cũ (công ty, chức danh, vai trò, email cũ).
        """
        contact_id = "CONT002"  # Lê Thị Thanh Thảo (đang ở CUST001 - VinaTech, vai trò influencer)
        old_info = get_contact(contact_id)
        self.assertEqual(old_info["customer_id"], "CUST001")
        self.assertEqual(old_info["job_title"], "Trưởng Bộ Phận Giải Pháp Doanh Nghiệp")
        self.assertEqual(old_info["buying_role"], "influencer")

        # Chuyển bà Thảo sang CUST002 (Global Mech) với chức danh Giám đốc CNTT, vai trò Người quyết định
        transferred = transfer_contact_to_new_customer(
            contact_id=contact_id,
            new_customer_id="CUST002",
            new_job_title="Giám Đốc Công Nghệ Thông Tin (CIO)",
            new_email="thao.le@globalmech.com.vn",
            new_phone="0987654321",
            new_buying_role="decision_maker",
            is_primary_at_new_customer=False,
            transfer_reason="Được bổ nhiệm sang Global Mech phụ trách hiện đại hóa hạ tầng.",
            sales_impact_note="Người quen cũ từ VinaTech, ủng hộ giải pháp của chúng ta, nay làm sếp lớn tại Global Mech!"
        )

        # 1. Kiểm tra thông tin hiện tại đã sang công ty mới
        self.assertEqual(transferred["customer_id"], "CUST002")
        self.assertEqual(transferred["job_title"], "Giám Đốc Công Nghệ Thông Tin (CIO)")
        self.assertEqual(transferred["email"], "thao.le@globalmech.com.vn")
        self.assertEqual(transferred["buying_role"], "decision_maker")

        # 2. Kiểm tra lịch sử công tác được bảo lưu nguyên vẹn
        history = transferred.get("history", [])
        self.assertEqual(len(history), 1, "Phải có đúng 1 bản ghi lịch sử công tác cũ")
        h0 = history[0]
        self.assertEqual(h0["previous_customer_id"], "CUST001")
        self.assertEqual(h0["previous_customer_name"], "Tập Đoàn Công Nghệ VinaTech")
        self.assertEqual(h0["previous_job_title"], "Trưởng Bộ Phận Giải Pháp Doanh Nghiệp")
        self.assertEqual(h0["previous_buying_role"], "influencer")
        self.assertEqual(h0["previous_email"], "thao.le@vinatech-group.vn")
        self.assertIn("Global Mech", h0["transfer_reason"])

    def test_tc4_seed_contact_with_history(self):
        """Kiểm tra người liên hệ CONT010 (Hoàng Minh Trí) đã có sẵn lịch sử chuyển từ CUST001 sang CUST004."""
        contact = get_contact("CONT010")
        self.assertIsNotNone(contact)
        self.assertEqual(contact["customer_id"], "CUST004")
        self.assertEqual(contact["buying_role"], "decision_maker")
        
        # Lịch sử công tác
        history = contact.get("history", [])
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["previous_customer_id"], "CUST001")
        self.assertEqual(history[0]["previous_buying_role"], "influencer")

    # ==========================================================================
    # KIỂM THỬ TẦNG WEB FLASK ROUTES & APIS
    # ==========================================================================
    def test_web_routes_and_views(self):
        """Kiểm thử các routes Flask cơ bản: trang chủ, danh sách khách hàng, ma trận mua, chi tiết liên hệ."""
        # 1. Trang chủ danh sách liên hệ
        res_index = self.app.get("/")
        self.assertEqual(res_index.status_code, 200)
        self.assertIn("Quản Lý Người Liên Hệ &amp; Vai Trò Quyết Định Mua", res_index.get_data(as_text=True))

        # 2. Trang danh sách khách hàng
        res_cust = self.app.get("/customers")
        self.assertEqual(res_cust.status_code, 200)
        self.assertIn("VinaTech", res_cust.get_data(as_text=True))

        # 3. Trang chi tiết Ma trận mua hàng của CUST001
        res_matrix = self.app.get("/customers/CUST001")
        self.assertEqual(res_matrix.status_code, 200)
        content = res_matrix.get_data(as_text=True)
        self.assertIn("Sơ Đồ Ma Trận Quyết Định Mua", content)
        self.assertIn("Người Quyết Định", content)
        self.assertIn("Người Cản Trở", content)

        # 4. Trang chi tiết người liên hệ CONT010 (có timeline lịch sử công tác)
        res_contact = self.app.get("/contacts/CONT010")
        self.assertEqual(res_contact.status_code, 200)
        contact_content = res_contact.get_data(as_text=True)
        self.assertIn("Hoàng Minh Trí", contact_content)
        self.assertIn("Lịch Sử Công Tác &amp; Dấu Vết Thương Vụ", contact_content)

    def test_web_transfer_contact_post(self):
        """Kiểm thử gửi POST chuyển công tác từ giao diện web."""
        res = self.app.post("/contacts/CONT003/transfer", data={
            "new_customer_id": "CUST003",
            "new_job_title": "Trưởng Nhóm Vận Hành Chi Nhánh",
            "new_email": "tuan.tran@asiaretail-fnb.com",
            "new_phone": "0903456789",
            "new_buying_role": "end_user",
            "transfer_reason": "Chuyển việc sang mảng bán lẻ F&B",
            "sales_impact_note": "Giữ liên lạc tốt để tư vấn phần mềm POS"
        }, follow_redirects=True)
        
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Chuyển công tác thành công", html)
        
        # Kiểm tra CONT003 trong database đã chuyển sang CUST003
        c = get_contact("CONT003")
        self.assertEqual(c["customer_id"], "CUST003")
        self.assertEqual(len(c["history"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
