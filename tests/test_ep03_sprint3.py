import io
import time
from datetime import datetime, timedelta
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.models.customer import Customer
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.support_ticket import SupportTicket


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# S3-01: HỒ SƠ KHÁCH HÀNG DOANH NGHIỆP & MST DUY NHẤT
# ==============================================================================

def test_s3_01_customer_crud_and_unique_mst(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]  # ALL scope

    # 1. Tạo khách hàng mới với MST hợp lệ (10 chữ số)
    create_payload = {
        "fullName": "Ông Nguyễn Văn Hưng",
        "company": "Công Ty Cổ Phần Công Nghệ Fictional 1",
        "taxCode": "0109998881",
        "email": "hung.nv@fictional1.vn",
        "phone": "0911223344",
        "status": "lead",
        "industry": "Công nghệ thông tin",
        "tier": "Enterprise",
        "location": "Hà Nội",
        "totalContractValue": 120000000.0,
    }
    res_create = client.post("/api/v1/customers", json=create_payload, headers=auth_header(token))
    assert res_create.status_code == 201
    created_data = res_create.json()
    assert created_data["taxCode"] == "0109998881"
    assert created_data["company"] == "Công Ty Cổ Phần Công Nghệ Fictional 1"
    customer_id = created_data["id"]

    # 2. Thử tạo khách hàng thứ hai trùng MST -> Bắt buộc báo lỗi 400
    dup_payload = {
        "fullName": "Bà Lê Thị Hương",
        "company": "Công Ty Trùng MST",
        "taxCode": "0109998881",
        "email": "huong.lt@trungmst.vn",
        "phone": "0988776655",
        "status": "lead",
    }
    res_dup = client.post("/api/v1/customers", json=dup_payload, headers=auth_header(token))
    assert res_dup.status_code == 400
    assert "Mã số thuế" in res_dup.json()["detail"] and "đã tồn tại" in res_dup.json()["detail"]

    # 3. Xem chi tiết khách hàng
    res_get = client.get(f"/api/v1/customers/{customer_id}", headers=auth_header(token))
    assert res_get.status_code == 200
    assert res_get.json()["id"] == customer_id

    # 4. Cập nhật khách hàng
    update_payload = {
        "company": "Công Ty Cổ Phần Fictional Đã Đổi Tên",
        "totalContractValue": 150000000.0,
    }
    res_update = client.put(f"/api/v1/customers/{customer_id}", json=update_payload, headers=auth_header(token))
    assert res_update.status_code == 200
    assert res_update.json()["company"] == "Công Ty Cổ Phần Fictional Đã Đổi Tên"
    assert res_update.json()["totalContractValue"] == 150000000.0

    # 5. Xóa mềm khách hàng
    res_delete = client.delete(f"/api/v1/customers/{customer_id}", headers=auth_header(token))
    assert res_delete.status_code == 204

    # Truy cập lại bản ghi đã xóa mềm -> 404
    res_reget = client.get(f"/api/v1/customers/{customer_id}", headers=auth_header(token))
    assert res_reget.status_code == 404


def test_s3_01_mst_format_validation(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]

    # MST không hợp lệ (ít hơn 10 số hoặc chứa ký tự đặc biệt sai)
    invalid_payload = {
        "fullName": "Trần Văn Sai",
        "company": "Công Ty MST Sai",
        "taxCode": "12345",  # chỉ có 5 số
        "email": "sai@mst.vn",
        "phone": "0912345678",
    }
    res = client.post("/api/v1/customers", json=invalid_payload, headers=auth_header(token))
    assert res.status_code == 422 or res.status_code == 400


# ==============================================================================
# S3-02: QUẢN LÝ NGƯỜI LIÊN HỆ & TRANSFER CONTACT
# ==============================================================================

def test_s3_02_contact_crud_and_transfer(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]
    cust_a_id = seed_data["customers"]["cust_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id

    # 1. Tạo người liên hệ cho Customer A với vai trò Decider
    contact_payload = {
        "fullName": "Nguyễn Giám Đốc Mua Hàng",
        "email": "giamdoc@muahang.vn",
        "phone": "0987112233",
        "position": "Giám đốc Mua hàng & Cung ứng",
        "role": "Decider",
        "isPrimary": True,
    }
    res_c = client.post(f"/api/v1/customers/{cust_a_id}/contacts", json=contact_payload, headers=auth_header(token))
    assert res_c.status_code == 201
    contact = res_c.json()
    assert contact["role"] == "Decider"
    assert contact["isPrimary"] is True
    contact_id = contact["id"]

    # 2. Lấy danh sách liên hệ của Customer A
    res_list = client.get(f"/api/v1/customers/{cust_a_id}/contacts", headers=auth_header(token))
    assert res_list.status_code == 200
    assert any(c["id"] == contact_id for c in res_list.json())

    # 3. Cập nhật thông tin người liên hệ
    res_up = client.put(
        f"/api/v1/contacts/{contact_id}",
        json={"position": "Phó Tổng Giám Đốc", "role": "Influencer"},
        headers=auth_header(token),
    )
    assert res_up.status_code == 200
    assert res_up.json()["position"] == "Phó Tổng Giám Đốc"
    assert res_up.json()["role"] == "Influencer"

    # 4. Điều chuyển người liên hệ sang Customer B (transfer_contact)
    res_trans = client.post(
        f"/api/v1/contacts/{contact_id}/transfer",
        json={"newCustomerId": cust_b_id, "reason": "Chuyển công tác sang công ty thành viên"},
        headers=auth_header(token),
    )
    assert res_trans.status_code == 200
    transferred = res_trans.json()
    assert transferred["customerId"] == cust_b_id

    # Kiểm tra Customer A không còn liên hệ này
    res_a_contacts = client.get(f"/api/v1/customers/{cust_a_id}/contacts", headers=auth_header(token))
    assert not any(c["id"] == contact_id for c in res_a_contacts.json())

    # Kiểm tra Customer B đã có liên hệ này
    res_b_contacts = client.get(f"/api/v1/customers/{cust_b_id}/contacts", headers=auth_header(token))
    assert any(c["id"] == contact_id for c in res_b_contacts.json())


# ==============================================================================
# S3-03: KHÁCH HÀNG 360 VIEW & HIỆU NĂNG 500 LOGS (< 1.5S)
# ==============================================================================

def test_s3_03_customer_360_view_and_performance(client: TestClient, seed_data: dict, db_session):
    token = seed_data["tokens"]["sales_director"]
    cust_a = seed_data["customers"]["cust_a"]
    user_admin = seed_data["users"]["emp_a"]

    # Tạo 500 bản ghi hoạt động (Activities) để kiểm thử hiệu năng
    activities = [
        Activity(
            customer_id=cust_a.id,
            user_id=user_admin.id,
            type="call",
            title=f"Cuộc gọi tư vấn thứ #{i}",
            description=f"Nội dung trao đổi chi tiết số {i} với đối tác doanh nghiệp.",
        )
        for i in range(500)
    ]
    db_session.add_all(activities)
    db_session.commit()

    # Bấm giờ truy vấn Customer 360 View
    start_time = time.time()
    response = client.get(f"/api/v1/customers/{cust_a.id}/360", headers=auth_header(token))
    elapsed_time = time.time() - start_time

    assert response.status_code == 200
    data = response.json()
    assert data["customer"]["id"] == cust_a.id
    assert len(data["activities"]) >= 500
    assert "contacts" in data
    assert "deals" in data
    assert "tickets" in data
    assert "documents" in data

    # Mục tiêu hiệu năng: response < 1.5 giây với 500 logs
    assert elapsed_time < 1.5, f"Thời gian phản hồi {elapsed_time:.3f}s vượt quá mục tiêu 1.5s"


# ==============================================================================
# S3-04: GỘP KHÁCH HÀNG TRÙNG LẶP (MERGE CUSTOMER)
# ==============================================================================

def test_s3_04_merge_duplicate_customer(client: TestClient, seed_data: dict, db_session):
    token = seed_data["tokens"]["sales_director"]

    # 1. Tạo 2 khách hàng riêng biệt: Master và Duplicate
    c_master = Customer(
        full_name="Nguyễn Văn Master",
        company="Tập Đoàn Master Corp",
        email="master@corp.vn",
        phone="0911000111",
        tax_code="0108889991",
        total_contract_value=100000000.0,
    )
    c_dup = Customer(
        full_name="Nguyễn Văn Duplicate",
        company="Công Ty Dup Co",
        email="dup@corp.vn",
        phone="0911000222",
        tax_code="0108889992",
        total_contract_value=50000000.0,
    )
    db_session.add_all([c_master, c_dup])
    db_session.commit()
    db_session.refresh(c_master)
    db_session.refresh(c_dup)

    # Thêm 1 Contact và 1 Deal vào duplicate
    dup_contact = Contact(
        customer_id=c_dup.id,
        full_name="Trần Phụ Trách Mua Hàng Dup",
        email="contact@dup.vn",
        phone="0933221100",
        role="Buyer",
    )
    dup_deal = Deal(
        customer_id=c_dup.id,
        owner_id=seed_data["users"]["emp_a"].id,
        title="Cơ hội bán hàng chuyển giao từ Dup",
        value=50000000.0,
        stage="proposal",
    )
    db_session.add_all([dup_contact, dup_deal])
    db_session.commit()

    # 2. Gọi API gộp khách hàng
    merge_payload = {
        "masterId": c_master.id,
        "duplicateId": c_dup.id,
        "fieldOverrides": {
            "phone": "0911000222",  # Lấy số điện thoại từ duplicate
        },
    }
    res_merge = client.post("/api/v1/customers/merge", json=merge_payload, headers=auth_header(token))
    assert res_merge.status_code == 200
    merged_data = res_merge.json()

    # Tổng giá trị hợp đồng được cộng dồn (100M + 50M = 150M)
    assert merged_data["totalContractValue"] == 150000000.0
    assert merged_data["phone"] == "0911000222"

    # Kiểm tra liên kết Contact và Deal đã chuyển sang Master
    res_contacts = client.get(f"/api/v1/customers/{c_master.id}/contacts", headers=auth_header(token))
    assert any(c["fullName"] == "Trần Phụ Trách Mua Hàng Dup" for c in res_contacts.json())

    # Khách hàng Duplicate đã bị xóa mềm
    res_dup_get = client.get(f"/api/v1/customers/{c_dup.id}", headers=auth_header(token))
    assert res_dup_get.status_code == 404

    # Kiểm tra không thể gộp một khách hàng vào chính nó
    res_self_merge = client.post(
        "/api/v1/customers/merge",
        json={"masterId": c_master.id, "duplicateId": c_master.id},
        headers=auth_header(token),
    )
    assert res_self_merge.status_code == 400


# ==============================================================================
# S3-05: CÔNG TY MẸ - CON (CORPORATE TREE & HIERARCHY)
# ==============================================================================

def test_s3_05_corporate_hierarchy_and_cycle_prevention(client: TestClient, seed_data: dict, db_session):
    token = seed_data["tokens"]["sales_director"]

    # 1. Tạo tập đoàn mẹ và 2 công ty con
    parent = Customer(
        full_name="Ông Phạm Nhật Vượng",
        company="Tập Đoàn Vingroup",
        email="corp@vingroup.vn",
        phone="02439749999",
        total_contract_value=500000000.0,
    )
    db_session.add(parent)
    db_session.commit()
    db_session.refresh(parent)

    child1 = Customer(
        full_name="VinFast Auto",
        company="Công Ty Cổ Phần VinFast",
        email="info@vinfast.vn",
        phone="1900232389",
        parent_customer_id=parent.id,
        total_contract_value=300000000.0,
    )
    child2 = Customer(
        full_name="Vinhomes Real Estate",
        company="Công Ty Cổ Phần Vinhomes",
        email="info@vinhomes.vn",
        phone="1900232388",
        parent_customer_id=parent.id,
        total_contract_value=200000000.0,
    )
    db_session.add_all([child1, child2])
    db_session.commit()
    db_session.refresh(child1)
    db_session.refresh(child2)

    # 2. Truy vấn cây phân cấp tập đoàn
    res_tree = client.get(f"/api/v1/customers/{parent.id}/hierarchy", headers=auth_header(token))
    assert res_tree.status_code == 200
    tree_data = res_tree.json()
    assert tree_data["company"] == "Tập Đoàn Vingroup"
    assert tree_data["totalContractValue"] == 500000000.0
    # Tổng doanh số toàn tập đoàn = 500M + 300M + 200M = 1.000.000.000
    assert tree_data["groupContractValue"] == 1000000000.0
    assert len(tree_data["children"]) == 2

    # 3. Ngăn chặn tự gán mẹ là chính mình
    res_self = client.put(f"/api/v1/customers/{parent.id}/parent?parent_id={parent.id}", headers=auth_header(token))
    assert res_self.status_code == 400

    # 4. Ngăn chặn tạo vòng lặp tham chiếu (Gán con VinFast làm mẹ của Vingroup)
    res_cycle = client.put(f"/api/v1/customers/{parent.id}/parent?parent_id={child1.id}", headers=auth_header(token))
    assert res_cycle.status_code == 400
    assert "vòng lặp tham chiếu" in res_cycle.json()["detail"]


# ==============================================================================
# S3-06: NHẬP KHÁCH HÀNG TỪ EXCEL (BULK UPSERT & VALIDATION)
# ==============================================================================

def test_s3_06_excel_import_and_bulk_upsert(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]

    # Chuẩn bị file Excel giả lập bằng Pandas
    df_data = {
        "Họ và tên": ["Nguyễn Excel 1", "Trần Excel 2", "Lê Thiếu Tên"],
        "Tên công ty": ["Công Ty TNHH Alpha", "Công Ty Cổ Phần Beta", ""],
        "Mã số thuế": ["0102233441", "0102233442", "0102233441"],  # Dòng 3 trùng MST và thiếu tên
        "Số điện thoại": ["0901234567", "0987654321", "0911"],
        "Email": ["alpha@corp.vn", "beta@corp.vn", "invalid-email"],
        "Lĩnh vực": ["Logistics", "Bán lẻ", "Khác"],
        "Giá trị hợp đồng": [80000000, 120000000, 0],
    }
    df = pd.DataFrame(df_data)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_bytes = excel_buffer.getvalue()

    # 1. Preview
    res_preview = client.post(
        "/api/v1/customers/import-preview",
        files={"file": ("test_customers.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(token),
    )
    assert res_preview.status_code == 200
    preview = res_preview.json()
    assert preview["totalRows"] == 3
    assert preview["validRows"] >= 2
    assert preview["invalidRows"] >= 1

    # 2. Execute Bulk Upsert
    res_import = client.post(
        "/api/v1/customers/import",
        files={"file": ("test_customers.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(token),
    )
    assert res_import.status_code == 200
    import_result = res_import.json()
    assert import_result["importedRows"] >= 2
    assert import_result["skippedRows"] >= 1


# ==============================================================================
# S3-07: BỘ LỌC NÂNG CAO & LƯU BỘ LỌC TÙY CHỈNH
# ==============================================================================

def test_s3_07_advanced_filtering_and_saved_presets(client: TestClient, seed_data: dict):
    token_director = seed_data["tokens"]["sales_director"]
    token_emp_a = seed_data["tokens"]["emp_a"]

    # 1. Lưu bộ lọc của Director
    preset_payload = {
        "name": "Bộ lọc khách hàng VIP IT",
        "entityType": "customer",
        "filterCriteria": '{"industry": "Công nghệ thông tin", "tier": "Enterprise", "minValue": 100000000}',
        "isDefault": True,
    }
    res_save = client.post("/api/v1/customer-filters", json=preset_payload, headers=auth_header(token_director))
    assert res_save.status_code == 201
    preset_id = res_save.json()["id"]

    # 2. Director lấy danh sách bộ lọc của mình -> Thấy preset
    res_get_filters = client.get("/api/v1/customer-filters", headers=auth_header(token_director))
    assert res_get_filters.status_code == 200
    assert any(p["id"] == preset_id for p in res_get_filters.json())

    # 3. Employee A lấy danh sách bộ lọc -> Không nhìn thấy bộ lọc của Director (Cách ly tuyệt đối)
    res_emp_filters = client.get("/api/v1/customer-filters", headers=auth_header(token_emp_a))
    assert not any(p["id"] == preset_id for p in res_emp_filters.json())

    # 4. Employee A cố tình xóa bộ lọc của Director -> Bị chặn 403 Forbidden
    res_hack_delete = client.delete(f"/api/v1/customer-filters/{preset_id}", headers=auth_header(token_emp_a))
    assert res_hack_delete.status_code == 403

    # 5. Director xóa bộ lọc thành công
    res_clean_delete = client.delete(f"/api/v1/customer-filters/{preset_id}", headers=auth_header(token_director))
    assert res_clean_delete.status_code == 204


# ==============================================================================
# S3-08: YÊU CẦU HỖ TRỢ & CỜ RỦI RO (TỰ ĐỘNG BẬT CỜ KHI QUÁ HẠN)
# ==============================================================================

def test_s3_08_support_tickets_and_overdue_risk_flag(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]
    cust_a = seed_data["customers"]["cust_a"]

    # 1. Tạo 2 ticket quá hạn (due_date trong quá khứ)
    yesterday = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    t1_payload = {
        "title": "Sự cố mất kết nối API Cổng thanh toán",
        "priority": "urgent",
        "dueDate": yesterday,
        "status": "open",
    }
    t2_payload = {
        "title": "Lỗi đồng bộ tồn kho thời gian thực",
        "priority": "high",
        "dueDate": yesterday,
        "status": "in_progress",
    }

    client.post(f"/api/v1/customers/{cust_a.id}/tickets", json=t1_payload, headers=auth_header(token))
    client.post(f"/api/v1/customers/{cust_a.id}/tickets", json=t2_payload, headers=auth_header(token))

    # 2. Kích hoạt quét tự động cờ rủi ro (Cron / Celery Task Trigger)
    res_scan = client.post("/api/v1/customers/scan-risks?threshold=2", headers=auth_header(token))
    assert res_scan.status_code == 200
    scan_result = res_scan.json()
    assert scan_result["flaggedCount"] >= 1

    # 3. Kiểm tra khách hàng A đã được tự động gắn cờ rủi ro
    res_risk = client.get(f"/api/v1/customers/{cust_a.id}/risk", headers=auth_header(token))
    assert res_risk.status_code == 200
    assert res_risk.json()["riskFlag"] is True
    assert "quá hạn" in res_risk.json()["riskReason"]


# ==============================================================================
# S3-09: DANH SÁCH CẦN CHĂM SÓC ĐỊNH KỲ & QUICK ACTION "ĐÃ LIÊN HỆ"
# ==============================================================================

def test_s3_09_stagnant_customers_and_quick_touch(client: TestClient, seed_data: dict, db_session):
    token = seed_data["tokens"]["sales_director"]
    cust_a = seed_data["customers"]["cust_a"]

    # Đặt thời điểm tương tác của cust_a về 45 ngày trước
    cust_a.last_interaction_at = datetime.utcnow() - timedelta(days=45)
    cust_a.total_contract_value = 250000000.0
    db_session.commit()

    # 1. Lấy danh sách khách hàng cần chăm sóc định kỳ (> 30 ngày)
    res_stagnant = client.get("/api/v1/customers/stagnant?days=30", headers=auth_header(token))
    assert res_stagnant.status_code == 200
    stagnant_list = res_stagnant.json()
    assert any(c["id"] == cust_a.id for c in stagnant_list)

    # 2. Thực hiện thao tác nhanh "Đã liên hệ" (Quick Touch)
    res_touch = client.post(f"/api/v1/customers/{cust_a.id}/quick-touch", headers=auth_header(token))
    assert res_touch.status_code == 200

    # 3. Kiểm tra lại danh sách stagnant: khách hàng này đã không còn nằm trong danh sách cần chăm sóc
    res_stagnant_after = client.get("/api/v1/customers/stagnant?days=30", headers=auth_header(token))
    assert not any(c["id"] == cust_a.id for c in res_stagnant_after.json())
