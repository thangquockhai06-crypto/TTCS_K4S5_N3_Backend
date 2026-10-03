"""
HỆ THỐNG QUẢN LÝ THÔNG TIN HỒ SƠ & DỮ LIỆU BÁO GIÁ (SCRUM-80)
============================================================
Ticket: SCRUM-69 / SCRUM-80
User Story:
  "Là người dùng của hệ thống, tôi muốn xem và cập nhật hồ sơ cá nhân,
   để chữ ký email của tôi luôn đúng khi gửi báo giá cho khách."

Tiêu chí chấp nhận:
  1. Sửa được họ tên, số điện thoại, chữ ký email.
  2. Không tự đổi được email, nhóm và vai trò (Bảo vệ đa tầng).
  3. Kiểm tra định dạng số điện thoại Việt Nam.
============================================================
"""

import re
import copy

# ==============================================================================
# 1. HÀM KIỂM TRA ĐỊNH DẠNG SỐ ĐIỆN THOẠI VIỆT NAM (TIÊU CHÍ 3)
# ==============================================================================
# Các đầu số di động hợp lệ tại Việt Nam (10 chữ số):
# - Viettel: 032-039, 086, 096-098
# - MobiFone: 070, 076-079, 089, 090, 093
# - VinaPhone: 081-085, 088, 091, 094
# - Vietnamobile: 052, 056, 058, 092
# - Gmobile / Itelecom / Wintel: 055, 059, 087, 099
VIETNAM_PHONE_REGEX = re.compile(
    r"^(?:\+?84|0)(3[2-9]|5[25689]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}$"
)

def clean_phone_number(phone_raw: str) -> str:
    """Làm sạch chuỗi số điện thoại: loại bỏ dấu cách, gạch nối, chấm, ngoặc đơn."""
    if not phone_raw:
        return ""
    cleaned = re.sub(r"[\s\.\-\(\)]+", "", phone_raw.strip())
    return cleaned

def validate_vietnam_phone(phone_raw: str):
    """
    Kiểm tra và chuẩn hóa số điện thoại di động Việt Nam.
    Trả về: (is_valid: bool, formatted_phone: str, error_message: str)
    """
    if not phone_raw or not phone_raw.strip():
        return False, "", "Số điện thoại không được để trống."
    
    cleaned = clean_phone_number(phone_raw)
    
    if not VIETNAM_PHONE_REGEX.match(cleaned):
        # Phân tích nguyên nhân lỗi cụ thể để phản hồi thân thiện
        digits_only = re.sub(r"\D", "", cleaned)
        if len(digits_only) < 10:
            msg = f"Số điện thoại '{phone_raw}' quá ngắn. Số điện thoại di động Việt Nam cần 10 chữ số."
        elif len(digits_only) > 11:
            msg = f"Số điện thoại '{phone_raw}' quá dài. Số điện thoại di động Việt Nam gồm 10 chữ số."
        else:
            msg = (
                f"Số điện thoại '{phone_raw}' không đúng định dạng mạng di động Việt Nam. "
                "Đầu số hợp lệ: 03x, 05x, 07x, 08x, 09x hoặc (+84)."
            )
        return False, "", msg
    
    # Chuẩn hóa về dạng hiển thị nội địa 0xxxxxxxxx
    if cleaned.startswith("+84"):
        normalized = "0" + cleaned[3:]
    elif cleaned.startswith("84") and len(cleaned) == 11:
        normalized = "0" + cleaned[2:]
    else:
        normalized = cleaned
        
    # Định dạng đẹp mắt: 0xxx xxx xxx
    pretty_phone = f"{normalized[:4]} {normalized[4:7]} {normalized[7:]}"
    return True, pretty_phone, ""

# ==============================================================================
# 2. DỮ LIỆU NGƯỜI DÙNG MẪU (USERS DATABASE)
# ==============================================================================
INITIAL_USERS = {
    "sales_rep": {
        "username": "sales_rep",
        "full_name": "Lê Hoàng Phúc",
        "phone": "0912 345 678",
        "email": "hoangphuc.le@enterprise-sales.vn",
        "role_code": "sales_rep",
        "role_name": "Chuyên viên kinh doanh",
        "business_group": "Nhóm Bán Lẻ Khu Vực Miền Bắc",
        "short_group": "Bán Lẻ Miền Bắc",
        "avatar_letters": "HP",
        "avatar_bg": "#059669",
        "email_signature": (
            "Trân trọng,\n"
            "Lê Hoàng Phúc | Chuyên viên kinh doanh\n"
            "Nhóm Bán Lẻ Khu Vực Miền Bắc - Enterprise Solution Corp\n"
            "Hotline/Zalo: 0912 345 678 | Email: hoangphuc.le@enterprise-sales.vn\n"
            "Địa chỉ: Tầng 12, Tòa nhà Landmark, Hà Nội"
        )
    },
    "team_lead": {
        "username": "team_lead",
        "full_name": "Trần Thị Mai Phương",
        "phone": "0987 654 321",
        "email": "maiphuong.tran@enterprise-sales.vn",
        "role_code": "team_lead",
        "role_name": "Trưởng nhóm kinh doanh",
        "business_group": "Nhóm Khách Hàng Doanh Nghiệp (B2B)",
        "short_group": "Nhóm B2B Doanh Nghiệp",
        "avatar_letters": "MP",
        "avatar_bg": "#2563eb",
        "email_signature": (
            "Trân trọng,\n"
            "Trần Thị Mai Phương | Trưởng nhóm kinh doanh B2B\n"
            "Enterprise Solution Corp\n"
            "Di động: 0987 654 321 | Email: maiphuong.tran@enterprise-sales.vn"
        )
    },
    "director": {
        "username": "director",
        "full_name": "Nguyễn Tuấn Anh",
        "phone": "0903 888 999",
        "email": "tuananh.nguyen@enterprise-sales.vn",
        "role_code": "director",
        "role_name": "Giám đốc kinh doanh",
        "business_group": "Ban Giám Đốc Kinh Doanh Toàn Quốc",
        "short_group": "BGĐ Kinh Doanh",
        "avatar_letters": "TA",
        "avatar_bg": "#7c3aed",
        "email_signature": (
            "Best Regards,\n"
            "Nguyen Tuan Anh | Sales Director\n"
            "Enterprise Solution Corp\n"
            "Phone: 0903 888 999 | Email: tuananh.nguyen@enterprise-sales.vn"
        )
    },
    "intern": {
        "username": "intern",
        "full_name": "Phạm Minh Khôi",
        "phone": "0934 112 233",
        "email": "minhkhoi.pham@enterprise-sales.vn",
        "role_code": "intern",
        "role_name": "Thực tập sinh kinh doanh",
        "business_group": "Nhóm Phát Triển Khách Hàng Mới",
        "short_group": "Khách Hàng Mới",
        "avatar_letters": "MK",
        "avatar_bg": "#d97706",
        "email_signature": (
            "Trân trọng,\n"
            "Phạm Minh Khôi | Thực tập sinh kinh doanh\n"
            "Enterprise Solution Corp\n"
            "SĐT: 0934 112 233 | Email: minhkhoi.pham@enterprise-sales.vn"
        )
    }
}

# Bộ nhớ lưu trữ dữ liệu phiên làm việc
USERS_DB = copy.deepcopy(INITIAL_USERS)

# ==============================================================================
# 3. QUY ĐỊNH BẢO MẬT & BẢO VỆ DỮ LIỆU ĐA TẦNG (TIÊU CHÍ 1 & 2)
# ==============================================================================
# Các trường người dùng ĐƯỢC PHÉP chỉnh sửa
EDITABLE_FIELDS = {"full_name", "phone", "email_signature"}

# Các trường BỊ CẤM TỰ ĐỔI (Chỉ hệ thống quản trị mới có quyền thay đổi)
PROTECTED_FIELDS = {"email", "role_code", "role_name", "business_group", "short_group", "username"}

def get_user(username: str):
    """Lấy thông tin người dùng theo username."""
    user = USERS_DB.get(username)
    if user:
        return copy.deepcopy(user)
    return None

def update_user_profile(username: str, form_data: dict):
    """
    Cập nhật hồ sơ cá nhân người dùng:
    - TIÊU CHÍ 1: Cho phép sửa full_name, phone, email_signature.
    - TIÊU CHÍ 2: Tuyệt đối KHÔNG CHO PHÉP sửa email, role, business_group.
                 Bảo vệ tầng backend: Dù client cố tình can thiệp gửi kèm email/role thì
                 hệ thống vẫn giữ nguyên giá trị gốc trong DB.
    - TIÊU CHÍ 3: Kiểm tra định dạng số điện thoại Việt Nam trước khi lưu.
    
    Trả về: (success: bool, message: str, updated_user: dict or None)
    """
    if username not in USERS_DB:
        return False, "Người dùng không tồn tại trong hệ thống.", None
    
    current_user = USERS_DB[username]
    
    # 1. Kiểm tra họ tên
    new_full_name = form_data.get("full_name", "").strip()
    if not new_full_name:
        return False, "Họ và tên không được để trống.", None
    if len(new_full_name) < 2 or len(new_full_name) > 100:
        return False, "Họ và tên phải có độ dài từ 2 đến 100 ký tự.", None
    
    # 2. Kiểm tra định dạng số điện thoại Việt Nam (Tiêu chí 3)
    new_phone_raw = form_data.get("phone", "").strip()
    is_valid_phone, formatted_phone, phone_error = validate_vietnam_phone(new_phone_raw)
    if not is_valid_phone:
        return False, phone_error, None
    
    # 3. Kiểm tra chữ ký email
    new_signature = form_data.get("email_signature", "").strip()
    if not new_signature:
        return False, "Chữ ký email không được để trống để đảm bảo tính chuyên nghiệp khi gửi báo giá.", None
    
    # 4. Phát hiện can thiệp vào các trường bị cấm (Tiêu chí 2)
    tampered_fields = []
    for field in PROTECTED_FIELDS:
        if field in form_data:
            submitted_val = str(form_data[field]).strip()
            original_val = str(current_user.get(field, "")).strip()
            if submitted_val and submitted_val != original_val:
                tampered_fields.append(field)
    
    # 5. Cập nhật CHỈ CÁC TRƯỜNG ĐƯỢC PHÉP (Editable whitelist)
    current_user["full_name"] = new_full_name
    current_user["phone"] = formatted_phone
    current_user["email_signature"] = new_signature
    
    # Cập nhật chữ cái đại diện avatar nếu đổi họ tên
    name_parts = new_full_name.split()
    if len(name_parts) >= 2:
        current_user["avatar_letters"] = (name_parts[0][0] + name_parts[-1][0]).upper()
    elif name_parts:
        current_user["avatar_letters"] = name_parts[0][:2].upper()
        
    msg = "Cập nhật hồ sơ cá nhân thành công!"
    if tampered_fields:
        field_names_vi = {
            "email": "Email",
            "role_code": "Vai trò",
            "role_name": "Vai trò",
            "business_group": "Nhóm kinh doanh"
        }
        vi_labels = [field_names_vi.get(f, f) for f in tampered_fields]
        msg += f" (Lưu ý: Các trường bảo mật [{', '.join(vi_labels)}] được giữ nguyên theo quy định)."
        
    return True, msg, copy.deepcopy(current_user)

def reset_database():
    """Khôi phục dữ liệu ban đầu cho các ca kiểm thử."""
    global USERS_DB
    USERS_DB = copy.deepcopy(INITIAL_USERS)

# ==============================================================================
# 4. DANH SÁCH BÁO GIÁ MẪU GỬI CHO KHÁCH HÀNG (ỨNG DỤNG THỰC TẾ CỦA CHỮ KÝ)
# ==============================================================================
SAMPLE_QUOTES = [
    {
        "id": "BG-2026-001",
        "customer_name": "Tập đoàn Công nghệ Alpha",
        "contact_person": "Ông Nguyễn Văn Hùng - Giám đốc CNTT",
        "customer_email": "hung.nguyen@alphacorp.vn",
        "project_title": "Báo giá Giải pháp Quản trị Doanh nghiệp ERP Cloud",
        "items": [
            {"name": "Gói bản quyền Core ERP Cloud (1 năm)", "qty": 1, "price": "180.000.000 ₫"},
            {"name": "Dịch vụ triển khai & đào tạo người dùng", "qty": 1, "price": "45.000.000 ₫"},
            {"name": "Gói hỗ trợ kỹ thuật 24/7 SLA Platinum", "qty": 12, "price": "60.000.000 ₫"}
        ],
        "total_amount": "285.000.000 ₫",
        "created_date": "02/10/2026",
        "status": "Chờ gửi"
    },
    {
        "id": "BG-2026-002",
        "customer_name": "Công ty Cổ phần Bán lẻ Đông Nam",
        "contact_person": "Bà Hoàng Thuỳ Trang - Trưởng phòng Thu mua",
        "customer_email": "trang.hoang@dongnamretail.vn",
        "project_title": "Báo giá Hệ thống POS Quản lý 20 Điểm Bán",
        "items": [
            {"name": "Thiết bị POS cảm ứng đa điểm", "qty": 20, "price": "160.000.000 ₫"},
            {"name": "Phần mềm quản lý chuỗi bán lẻ Retail Pro", "qty": 1, "price": "75.000.000 ₫"}
        ],
        "total_amount": "235.000.000 ₫",
        "created_date": "01/10/2026",
        "status": "Chờ gửi"
    }
]
