"""
MODULE QUẢN LÝ DỮ LIỆU & NGHIỆP VỤ NGƯỜI LIÊN HỆ & VAI TRÒ MUA HÀNG
===================================================================
Mã Nhiệm Vụ: SCRUM-50 / SCRUM-58
User Story:
    "Là Nhân viên kinh doanh, tôi muốn quản lý người liên hệ và vai trò của họ
     trong quyết định mua, để biết phải thuyết phục ai và ai là người có thể cản thương vụ."

Đáp ứng đầy đủ 4 Tiêu chí chấp nhận:
    1. Mỗi khách hàng có nhiều người liên hệ, mỗi người có chức danh, email, số điện thoại.
    2. Đánh dấu vai trò trong quyết định mua: người quyết định, người ảnh hưởng,
       người dùng cuối, người cản trở.
    3. Đánh dấu một người là đầu mối chính (mỗi khách hàng chỉ có 1 đầu mối chính tại một thời điểm).
    4. Một người liên hệ chuyển sang công ty khác thì gắn lại được sang khách hàng mới,
       giữ nguyên toàn bộ lịch sử công tác và vai trò cũ.
===================================================================
"""

import re
import copy
from datetime import datetime
from typing import Dict, List, Optional, Any


# ==============================================================================
# ĐỊNH NGHĨA 4 VAI TRÒ TRONG QUYẾT ĐỊNH MUA (BUYING DECISION ROLES)
# ==============================================================================
BUYING_ROLES = {
    "decision_maker": {
        "id": "decision_maker",
        "name": "Người quyết định",
        "icon": "🎯",
        "badge_class": "badge-decision",
        "color": "#1e40af",  # Xanh dương đậm
        "bg_color": "#dbeafe",
        "description": "Người có quyền lực tối cao, thẩm quyền ký duyệt hợp đồng và quyết định phân bổ ngân sách.",
        "sales_strategy": "Tập trung vào tỷ suất sinh lời (ROI), thời gian thu hồi vốn, tính an toàn và giá trị chiến lược dài hạn."
    },
    "influencer": {
        "id": "influencer",
        "name": "Người ảnh hưởng",
        "icon": "💡",
        "badge_class": "badge-influencer",
        "color": "#6b21a8",  # Tím sang trọng
        "bg_color": "#f3e8ff",
        "description": "Chuyên gia kỹ thuật, cố vấn hoặc quản lý bộ phận có tiếng nói trọng lượng tác động lên quyết định.",
        "sales_strategy": "Cung cấp tài liệu kỹ thuật chuyên sâu, so sánh tính năng (benchmark), bản thử nghiệm (PoC) và chứng chỉ chất lượng."
    },
    "end_user": {
        "id": "end_user",
        "name": "Người dùng cuối",
        "icon": "👤",
        "badge_class": "badge-user",
        "color": "#065f46",  # Xanh lục bảo
        "bg_color": "#d1fae5",
        "description": "Nhân sự trực tiếp sử dụng sản phẩm hàng ngày; quan tâm nhất đến trải nghiệm tiện lợi, giảm tải áp lực.",
        "sales_strategy": "Trình diễn giao diện trực quan, tính năng tự động hóa, thao tác đơn giản và hỗ trợ đào tạo bài bản."
    },
    "blocker": {
        "id": "blocker",
        "name": "Người cản trở",
        "icon": "⚠️",
        "badge_class": "badge-blocker",
        "color": "#991b1b",  # Đỏ cảnh báo
        "bg_color": "#fee2e2",
        "description": "Người có tâm lý phản đối, lo ngại rủi ro, sợ mất vị thế hoặc gắn bó sâu đậm với nhà cung cấp cũ.",
        "sales_strategy": "Tìm hiểu nỗi sợ thầm kín, tổ chức gặp riêng lắng nghe, cung cấp cam kết chuyển đổi êm thấm và bảo lưu dữ liệu cũ."
    }
}


# ==============================================================================
# HÀM XÁC THỰC DỮ LIỆU (VALIDATORS)
# ==============================================================================
VN_PHONE_REGEX = re.compile(r"^(?:\+?84|0)(3[2-9]|5[25689]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_phone_number(phone: str) -> bool:
    """Kiểm tra số điện thoại Việt Nam hợp lệ (10 chữ số, đúng đầu số nhà mạng)."""
    if not phone:
        return False
    clean_phone = re.sub(r"[\s.-]", "", phone.strip())
    return bool(VN_PHONE_REGEX.match(clean_phone))


def validate_email_address(email: str) -> bool:
    """Kiểm tra địa chỉ email đúng định dạng tiêu chuẩn."""
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


# ==============================================================================
# DỮ LIỆU BAN ĐẦU (SEED DATA MẪU DOANH NGHIỆP THỰC TẾ)
# ==============================================================================
INITIAL_CUSTOMERS: Dict[str, Dict[str, Any]] = {
    "CUST001": {
        "id": "CUST001",
        "name": "Tập Đoàn Công Nghệ VinaTech",
        "code": "VINATECH",
        "industry": "Công nghệ thông tin & Viễn thông",
        "scale": "500 - 1000 nhân sự",
        "address": "Tầng 12, Keangnam Landmark 72, Nam Từ Liêm, Hà Nội",
        "website": "https://vinatech-group.vn",
        "status": "Đang đàm phán hợp đồng Enterprise",
        "estimated_value": 450000000,  # 450 triệu VNĐ
        "created_at": "2026-01-15 09:00:00"
    },
    "CUST002": {
        "id": "CUST002",
        "name": "Tổng Công Ty Cơ Khí & Chế Tạo Toàn Cầu (Global Mech)",
        "code": "GLOB_MECH",
        "industry": "Sản xuất cơ khí công nghiệp nặng",
        "scale": "1,200 nhân sự",
        "address": "Khu công nghiệp VSIP I, Thuận An, Bình Dương",
        "website": "https://globalmech.com.vn",
        "status": "Đã gửi đề xuất giải pháp & Demo",
        "estimated_value": 720000000,  # 720 triệu VNĐ
        "created_at": "2026-02-10 14:30:00"
    },
    "CUST003": {
        "id": "CUST003",
        "name": "Công Ty Cổ Phần Bán Lẻ & Chuỗi F&B Á Châu",
        "code": "ASIA_RETAIL",
        "industry": "Bán lẻ đa kênh & Chuỗi đồ uống",
        "scale": "350 nhân sự",
        "address": "Số 88 Hai Bà Trưng, Quận 1, TP. Hồ Chí Minh",
        "website": "https://asiaretail-fnb.com",
        "status": "Khách hàng mới tiếp cận (Lead ấm)",
        "estimated_value": 280000000,  # 280 triệu VNĐ
        "created_at": "2026-03-01 10:15:00"
    },
    "CUST004": {
        "id": "CUST004",
        "name": "Tập Đoàn Tài Chính & Đầu Tư Nam Á",
        "code": "NAMA_INVEST",
        "industry": "Tài chính & Quản lý quỹ đầu tư",
        "scale": "800 nhân sự",
        "address": "Tòa nhà Vietcombank Tower, Quận 1, TP. Hồ Chí Minh",
        "website": "https://namainvest.vn",
        "status": "Thương vụ đang bị tắc do người cản trở",
        "estimated_value": 950000000,  # 950 triệu VNĐ
        "created_at": "2026-03-20 16:45:00"
    }
}

INITIAL_CONTACTS: Dict[str, Dict[str, Any]] = {
    # ----------------------------------------------------
    # KHÁCH HÀNG CUST001: VinaTech Group
    # ----------------------------------------------------
    "CONT001": {
        "id": "CONT001",
        "customer_id": "CUST001",
        "full_name": "Nguyễn Hoàng Nam",
        "job_title": "Giám Đốc Công Nghệ (CTO)",
        "email": "nam.nguyen@vinatech-group.vn",
        "phone": "0912345678",
        "buying_role": "decision_maker",
        "is_primary": True,  # Đầu mối chính của CUST001
        "notes": "Quan tâm đến bảo mật đa tầng và khả năng mở rộng hệ thống đám mây.",
        "support_level": "Rất ủng hộ",
        "created_at": "2026-01-16 10:00:00",
        "history": []
    },
    "CONT002": {
        "id": "CONT002",
        "customer_id": "CUST001",
        "full_name": "Lê Thị Thanh Thảo",
        "job_title": "Trưởng Bộ Phận Giải Pháp Doanh Nghiệp",
        "email": "thao.le@vinatech-group.vn",
        "phone": "0987654321",
        "buying_role": "influencer",
        "is_primary": False,
        "notes": "Người đánh giá trực tiếp PoC và chấm điểm kỹ thuật các nhà thầu.",
        "support_level": "Ủng hộ",
        "created_at": "2026-01-18 11:30:00",
        "history": []
    },
    "CONT003": {
        "id": "CONT003",
        "customer_id": "CUST001",
        "full_name": "Trần Anh Tuấn",
        "job_title": "Chuyên Viên Vận Hành Hệ Thống",
        "email": "tuan.tran@vinatech-group.vn",
        "phone": "0903456789",
        "buying_role": "end_user",
        "is_primary": False,
        "notes": "Cần giải pháp có tài liệu hướng dẫn tiếng Việt và API rõ ràng.",
        "support_level": "Trung lập",
        "created_at": "2026-01-20 14:00:00",
        "history": []
    },
    "CONT004": {
        "id": "CONT004",
        "customer_id": "CUST001",
        "full_name": "Vũ Đình Khải",
        "job_title": "Trưởng Phòng Quản Lý Chi Phí & Kiểm Toán",
        "email": "khai.vu@vinatech-group.vn",
        "phone": "0978901234",
        "buying_role": "blocker",
        "is_primary": False,
        "notes": "E ngại chi phí bản quyền định kỳ hàng năm vượt ngân sách dự toán ban đầu.",
        "support_level": "Phản đối",
        "created_at": "2026-01-25 15:45:00",
        "history": []
    },

    # ----------------------------------------------------
    # KHÁCH HÀNG CUST002: Global Mech
    # ----------------------------------------------------
    "CONT005": {
        "id": "CONT005",
        "customer_id": "CUST002",
        "full_name": "Phạm Văn Long",
        "job_title": "Phó Tổng Giám Đốc Sản Xuất",
        "email": "long.pham@globalmech.com.vn",
        "phone": "0934567890",
        "buying_role": "decision_maker",
        "is_primary": True,  # Đầu mối chính của CUST002
        "notes": "Người quyết định chuyển đổi số toàn bộ 3 phân xưởng cơ khí.",
        "support_level": "Rất ủng hộ",
        "created_at": "2026-02-12 09:20:00",
        "history": []
    },
    "CONT006": {
        "id": "CONT006",
        "customer_id": "CUST002",
        "full_name": "Đặng Quốc Hưng",
        "job_title": "Kỹ Sư Trưởng Nhà Máy",
        "email": "hung.dang@globalmech.com.vn",
        "phone": "0967890123",
        "buying_role": "influencer",
        "is_primary": False,
        "notes": "Yêu cầu kết nối dữ liệu trực tiếp với máy CNC và dây chuyền tự động.",
        "support_level": "Ủng hộ",
        "created_at": "2026-02-14 10:15:00",
        "history": []
    },
    "CONT007": {
        "id": "CONT007",
        "customer_id": "CUST002",
        "full_name": "Hoàng Thị Mai",
        "job_title": "Trưởng Phòng Mua Hàng & Cung Ứng",
        "email": "mai.hoang@globalmech.com.vn",
        "phone": "0945678901",
        "buying_role": "blocker",
        "is_primary": False,
        "notes": "Thích đối tác quen truyền thống hơn là áp dụng giải pháp phần mềm mới.",
        "support_level": "Nghi ngờ",
        "created_at": "2026-02-18 16:30:00",
        "history": []
    },

    # ----------------------------------------------------
    # KHÁCH HÀNG CUST003: Asia Retail & F&B
    # ----------------------------------------------------
    "CONT008": {
        "id": "CONT008",
        "customer_id": "CUST003",
        "full_name": "Bùi Đức Thịnh",
        "job_title": "Giám Đốc Vận Hành Chuỗi (COO)",
        "email": "thinh.bui@asiaretail-fnb.com",
        "phone": "0918765432",
        "buying_role": "decision_maker",
        "is_primary": True,  # Đầu mối chính của CUST003
        "notes": "Muốn đồng bộ dữ liệu doanh thu giữa 45 chi nhánh cửa hàng tức thì.",
        "support_level": "Rất ủng hộ",
        "created_at": "2026-03-02 08:30:00",
        "history": []
    },
    "CONT009": {
        "id": "CONT009",
        "customer_id": "CUST003",
        "full_name": "Võ Phương Uyên",
        "job_title": "Quản Lý Cửa Hàng Trưởng Flagship",
        "email": "uyen.vo@asiaretail-fnb.com",
        "phone": "0976543210",
        "buying_role": "end_user",
        "is_primary": False,
        "notes": "Ưu tiên tốc độ quét mã vạch và giao diện thu ngân cảm ứng 1 chạm.",
        "support_level": "Ủng hộ",
        "created_at": "2026-03-05 13:45:00",
        "history": []
    },

    # ----------------------------------------------------
    # KHÁCH HÀNG CUST004: Nam Á Investment
    # ĐẶC BIỆT: CONT010 là người đã từng công tác ở CUST001 trước đây!
    # Thể hiện Tiêu chí 4: Chuyển công tác giữ nguyên toàn bộ lịch sử!
    # ----------------------------------------------------
    "CONT010": {
        "id": "CONT010",
        "customer_id": "CUST004",
        "full_name": "Hoàng Minh Trí",
        "job_title": "Giám Đốc Chuyển Đổi Số (CDO)",
        "email": "tri.hoang@namainvest.vn",
        "phone": "0909123456",
        "buying_role": "decision_maker",
        "is_primary": True,  # Đầu mối chính hiện tại của CUST004
        "notes": "Mối quan hệ thân thiết từ khi làm việc tại VinaTech; rất tin tưởng đội ngũ tư vấn của chúng ta.",
        "support_level": "Rất ủng hộ",
        "created_at": "2026-03-21 09:00:00",
        "history": [
            {
                "previous_customer_id": "CUST001",
                "previous_customer_name": "Tập Đoàn Công Nghệ VinaTech",
                "previous_job_title": "Phó Giám Đốc Trung Tâm R&D",
                "previous_buying_role": "influencer",
                "previous_email": "tri.hoang@vinatech-group.vn",
                "previous_phone": "0909123456",
                "was_primary": False,
                "transferred_at": "2026-03-15 10:00:00",
                "transfer_reason": "Được Tập đoàn Nam Á săn đón (headhunt) sang làm Giám đốc Chuyển đổi số cấp cao.",
                "sales_impact_note": "Cơ hội vàng cho sales: Người quen cũ lên chức vụ cao hơn tại khách hàng lớn mới!"
            }
        ]
    },
    "CONT011": {
        "id": "CONT011",
        "customer_id": "CUST004",
        "full_name": "Trịnh Quốc Bảo",
        "job_title": "Trưởng Ban Quản Trị Rủi Ro & Tuân Thủ",
        "email": "bao.trinh@namainvest.vn",
        "phone": "0981234567",
        "buying_role": "blocker",
        "is_primary": False,
        "notes": "Đang cản trở vì yêu cầu chứng chỉ ISO 27001 và máy chủ lưu trữ phải đặt tại Việt Nam.",
        "support_level": "Phản đối mạnh",
        "created_at": "2026-03-22 14:15:00",
        "history": []
    }
}


# ==============================================================================
# BỘ NHỚ LÀM VIỆC TRONG PHIÊN (STATEFUL RUNTIME DATABASE)
# ==============================================================================
DB_CUSTOMERS: Dict[str, Dict[str, Any]] = copy.deepcopy(INITIAL_CUSTOMERS)
DB_CONTACTS: Dict[str, Dict[str, Any]] = copy.deepcopy(INITIAL_CONTACTS)


def reset_database() -> None:
    """Khôi phục toàn bộ dữ liệu mẫu ban đầu (phục vụ kiểm thử và demo)."""
    global DB_CUSTOMERS, DB_CONTACTS
    DB_CUSTOMERS = copy.deepcopy(INITIAL_CUSTOMERS)
    DB_CONTACTS = copy.deepcopy(INITIAL_CONTACTS)


# ==============================================================================
# CÁC HÀM XỬ LÝ KHÁCH HÀNG (CUSTOMER CRUD & METRICS)
# ==============================================================================
def get_all_customers() -> List[Dict[str, Any]]:
    """Lấy danh sách tất cả các khách hàng kèm tổng số người liên hệ và đầu mối chính."""
    result = []
    for cust_id, cust in DB_CUSTOMERS.items():
        cust_copy = copy.deepcopy(cust)
        # Tìm danh sách người liên hệ của khách hàng này
        contacts = get_contacts_by_customer(cust_id)
        cust_copy["contact_count"] = len(contacts)
        primary = next((c for c in contacts if c.get("is_primary")), None)
        cust_copy["primary_contact"] = primary
        
        # Thống kê nhanh số lượng 4 vai trò mua
        role_counts = {role: 0 for role in BUYING_ROLES.keys()}
        for c in contacts:
            r = c.get("buying_role")
            if r in role_counts:
                role_counts[r] += 1
        cust_copy["role_counts"] = role_counts
        
        result.append(cust_copy)
    return result


def get_customer(customer_id: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin chi tiết một khách hàng theo ID."""
    cust = DB_CUSTOMERS.get(customer_id)
    return copy.deepcopy(cust) if cust else None


def create_customer(
    name: str,
    code: str,
    industry: str,
    scale: str,
    address: str,
    website: str,
    status: str = "Tiếp cận ban đầu",
    estimated_value: int = 0
) -> Dict[str, Any]:
    """Tạo mới một khách hàng doanh nghiệp."""
    new_id = f"CUST{len(DB_CUSTOMERS) + 1:03d}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    customer_data = {
        "id": new_id,
        "name": name.strip(),
        "code": code.strip().upper(),
        "industry": industry.strip(),
        "scale": scale.strip(),
        "address": address.strip(),
        "website": website.strip(),
        "status": status.strip(),
        "estimated_value": int(estimated_value or 0),
        "created_at": now_str
    }
    DB_CUSTOMERS[new_id] = customer_data
    return copy.deepcopy(customer_data)


# ==============================================================================
# CÁC HÀM XỬ LÝ NGƯỜI LIÊN HỆ & VAI TRÒ MUA HÀNG (CONTACTS & BUYING ROLES)
# ==============================================================================
def get_all_contacts(
    customer_id: Optional[str] = None,
    buying_role: Optional[str] = None,
    keyword: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Lấy danh sách người liên hệ có hỗ trợ tìm kiếm và lọc:
    - customer_id: Lọc theo khách hàng cụ thể
    - buying_role: Lọc theo 1 trong 4 vai trò mua (decision_maker, influencer, end_user, blocker)
    - keyword: Tìm kiếm theo tên, chức danh, email, SĐT
    """
    results = []
    kw = keyword.strip().lower() if keyword else None

    for contact_id, contact in DB_CONTACTS.items():
        if customer_id and contact.get("customer_id") != customer_id:
            continue
        if buying_role and contact.get("buying_role") != buying_role:
            continue
        if kw:
            matches_kw = (
                kw in contact.get("full_name", "").lower()
                or kw in contact.get("job_title", "").lower()
                or kw in contact.get("email", "").lower()
                or kw in contact.get("phone", "").lower()
            )
            if not matches_kw:
                continue

        c_copy = copy.deepcopy(contact)
        # Gắn thêm thông tin tên công ty hiện tại
        cust = DB_CUSTOMERS.get(c_copy.get("customer_id"))
        c_copy["customer_name"] = cust.get("name") if cust else "Không xác định"
        # Gắn metadata của vai trò mua
        role_meta = BUYING_ROLES.get(c_copy.get("buying_role"))
        c_copy["role_meta"] = role_meta
        results.append(c_copy)

    return results


def get_contacts_by_customer(customer_id: str) -> List[Dict[str, Any]]:
    """Lấy danh sách toàn bộ người liên hệ thuộc một khách hàng."""
    return get_all_contacts(customer_id=customer_id)


def get_contact(contact_id: str) -> Optional[Dict[str, Any]]:
    """Lấy chi tiết một người liên hệ theo ID kèm lịch sử công tác đầy đủ."""
    contact = DB_CONTACTS.get(contact_id)
    if not contact:
        return None
    c_copy = copy.deepcopy(contact)
    cust = DB_CUSTOMERS.get(c_copy.get("customer_id"))
    c_copy["customer_name"] = cust.get("name") if cust else "Không xác định"
    c_copy["role_meta"] = BUYING_ROLES.get(c_copy.get("buying_role"))
    return c_copy


def add_contact(
    customer_id: str,
    full_name: str,
    job_title: str,
    email: str,
    phone: str,
    buying_role: str,
    is_primary: bool = False,
    notes: str = "",
    support_level: str = "Ủng hộ"
) -> Dict[str, Any]:
    """
    Thêm mới một người liên hệ cho khách hàng.
    Đáp ứng Tiêu chí 1: Đầy đủ chức danh, email, số điện thoại.
    Đáp ứng Tiêu chí 2: Đánh dấu đúng 1 trong 4 vai trò mua.
    Đáp ứng Tiêu chí 3: Nếu được đánh dấu là đầu mối chính, tự động gỡ cờ đầu mối chính cũ.
    """
    if customer_id not in DB_CUSTOMERS:
        raise ValueError(f"Khách hàng với mã {customer_id} không tồn tại!")
    if not full_name.strip():
        raise ValueError("Họ và tên người liên hệ không được để trống!")
    if not job_title.strip():
        raise ValueError("Chức danh không được để trống!")
    if not validate_email_address(email):
        raise ValueError(f"Địa chỉ email '{email}' không đúng định dạng!")
    if not validate_phone_number(phone):
        raise ValueError(f"Số điện thoại '{phone}' không đúng định dạng số di động Việt Nam!")
    if buying_role not in BUYING_ROLES:
        raise ValueError(f"Vai trò mua '{buying_role}' không hợp lệ! Chỉ chấp nhận: {list(BUYING_ROLES.keys())}")

    # Tạo mã ID mới
    new_id = f"CONT{len(DB_CONTACTS) + 1:03d}"
    # Nếu trùng do xóa trước đó, sinh id duy nhất
    counter = len(DB_CONTACTS) + 1
    while new_id in DB_CONTACTS:
        counter += 1
        new_id = f"CONT{counter:03d}"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Nếu người này được chọn là đầu mối chính -> gỡ cờ đầu mối chính của các người khác trong cùng khách hàng
    if is_primary:
        for cid, cinfo in DB_CONTACTS.items():
            if cinfo.get("customer_id") == customer_id:
                cinfo["is_primary"] = False
    else:
        # Nếu khách hàng này chưa có ai là đầu mối chính, tự động đặt người đầu tiên làm đầu mối chính
        existing = [c for c in DB_CONTACTS.values() if c.get("customer_id") == customer_id and c.get("is_primary")]
        if not existing:
            is_primary = True

    contact_data = {
        "id": new_id,
        "customer_id": customer_id,
        "full_name": full_name.strip(),
        "job_title": job_title.strip(),
        "email": email.strip().lower(),
        "phone": re.sub(r"[\s.-]", "", phone.strip()),
        "buying_role": buying_role,
        "is_primary": bool(is_primary),
        "notes": notes.strip(),
        "support_level": support_level.strip(),
        "created_at": now_str,
        "history": []
    }

    DB_CONTACTS[new_id] = contact_data
    return copy.deepcopy(contact_data)


def update_contact(
    contact_id: str,
    full_name: str,
    job_title: str,
    email: str,
    phone: str,
    buying_role: str,
    is_primary: bool,
    notes: str = "",
    support_level: str = "Ủng hộ"
) -> Dict[str, Any]:
    """Cập nhật thông tin người liên hệ."""
    if contact_id not in DB_CONTACTS:
        raise ValueError(f"Không tìm thấy người liên hệ với mã {contact_id}!")
    if not full_name.strip():
        raise ValueError("Họ và tên không được để trống!")
    if not job_title.strip():
        raise ValueError("Chức danh không được để trống!")
    if not validate_email_address(email):
        raise ValueError(f"Email '{email}' không hợp lệ!")
    if not validate_phone_number(phone):
        raise ValueError(f"Số điện thoại '{phone}' không hợp lệ!")
    if buying_role not in BUYING_ROLES:
        raise ValueError(f"Vai trò mua '{buying_role}' không hợp lệ!")

    contact = DB_CONTACTS[contact_id]
    customer_id = contact["customer_id"]

    # Xử lý cờ đầu mối chính
    if is_primary:
        for cid, cinfo in DB_CONTACTS.items():
            if cinfo.get("customer_id") == customer_id:
                cinfo["is_primary"] = False
        contact["is_primary"] = True
    else:
        # Nếu đang là đầu mối chính mà bỏ chọn, kiểm tra xem có ai khác không
        contact["is_primary"] = False

    contact["full_name"] = full_name.strip()
    contact["job_title"] = job_title.strip()
    contact["email"] = email.strip().lower()
    contact["phone"] = re.sub(r"[\s.-]", "", phone.strip())
    contact["buying_role"] = buying_role
    contact["notes"] = notes.strip()
    contact["support_level"] = support_level.strip()

    return copy.deepcopy(contact)


def set_primary_contact(customer_id: str, contact_id: str) -> bool:
    """
    Đánh dấu một người làm đầu mối chính (Primary Contact) cho khách hàng.
    Đáp ứng Tiêu chí 3: Chỉ duy nhất 1 người là đầu mối chính, người cũ tự động gỡ cờ.
    """
    if customer_id not in DB_CUSTOMERS:
        raise ValueError(f"Khách hàng {customer_id} không tồn tại!")
    if contact_id not in DB_CONTACTS:
        raise ValueError(f"Người liên hệ {contact_id} không tồn tại!")

    target_contact = DB_CONTACTS[contact_id]
    if target_contact.get("customer_id") != customer_id:
        raise ValueError(f"Người liên hệ {contact_id} không thuộc khách hàng {customer_id}!")

    # Gỡ cờ của tất cả người liên hệ trong cùng khách hàng
    for cid, cinfo in DB_CONTACTS.items():
        if cinfo.get("customer_id") == customer_id:
            cinfo["is_primary"] = False

    # Đặt cờ cho người được chọn
    target_contact["is_primary"] = True
    return True


def delete_contact(contact_id: str) -> bool:
    """Xóa một người liên hệ."""
    if contact_id in DB_CONTACTS:
        was_primary = DB_CONTACTS[contact_id].get("is_primary")
        cust_id = DB_CONTACTS[contact_id].get("customer_id")
        del DB_CONTACTS[contact_id]
        
        # Nếu người bị xóa là đầu mối chính, tự động gán người đầu tiên còn lại làm đầu mối chính
        if was_primary:
            remaining = [c for c in DB_CONTACTS.values() if c.get("customer_id") == cust_id]
            if remaining:
                remaining[0]["is_primary"] = True
        return True
    return False


# ==============================================================================
# TIÊU CHÍ 4: CHUYỂN CÔNG TÁC SANG CÔNG TY MỚI & LƯU VẾT LỊCH SỬ NGUYÊN VẸN
# ==============================================================================
def transfer_contact_to_new_customer(
    contact_id: str,
    new_customer_id: str,
    new_job_title: str,
    new_email: Optional[str] = None,
    new_phone: Optional[str] = None,
    new_buying_role: Optional[str] = None,
    is_primary_at_new_customer: bool = False,
    transfer_reason: str = "",
    sales_impact_note: str = ""
) -> Dict[str, Any]:
    """
    Gắn người liên hệ sang khách hàng mới khi họ chuyển công tác,
    đồng thời lưu lại toàn bộ lịch sử công tác (giữ nguyên lịch sử).
    
    Quy trình chuẩn B2B CRM:
    1. Đóng băng và ghi lại snapshot lịch sử tại công ty cũ (Tên công ty cũ, chức danh cũ,
       vai trò mua cũ, email cũ, trạng thái đầu mối chính cũ, ngày chuyển đi).
    2. Cập nhật người liên hệ sang công ty mới với:
       - Mã khách hàng mới (`customer_id = new_customer_id`)
       - Chức danh mới (`new_job_title`)
       - Email mới tại công ty mới (hoặc giữ nguyên nếu không đổi)
       - Số điện thoại mới (hoặc giữ nguyên)
       - Vai trò quyết định mua mới tại công ty mới
    3. Xử lý đầu mối chính:
       - Tại công ty cũ: Nếu người này từng là đầu mối chính, tự động chỉ định người kế nhiệm
         (người liên hệ tiếp theo) làm đầu mối chính mới để công ty cũ không bị khuyết đầu mối.
       - Tại công ty mới: Nếu `is_primary_at_new_customer = True`, gọi `set_primary_contact`.
    4. Thêm bản ghi lịch sử vào mảng `contact['history']` với thứ tự thời gian mới nhất lên đầu.
    """
    if contact_id not in DB_CONTACTS:
        raise ValueError(f"Không tìm thấy người liên hệ {contact_id}!")
    if new_customer_id not in DB_CUSTOMERS:
        raise ValueError(f"Khách hàng mới {new_customer_id} không tồn tại!")
    if not new_job_title.strip():
        raise ValueError("Chức danh mới tại công ty mới không được để trống!")

    contact = DB_CONTACTS[contact_id]
    old_customer_id = contact["customer_id"]

    if old_customer_id == new_customer_id:
        raise ValueError("Người liên hệ hiện đã thuộc công ty này rồi! Vui lòng chọn một công ty khác.")

    old_cust = DB_CUSTOMERS.get(old_customer_id)
    old_cust_name = old_cust.get("name") if old_cust else "Công ty cũ"
    new_cust = DB_CUSTOMERS.get(new_customer_id)
    new_cust_name = new_cust.get("name") if new_cust else "Công ty mới"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Tạo snapshot lưu lịch sử công tác cũ
    history_record = {
        "previous_customer_id": old_customer_id,
        "previous_customer_name": old_cust_name,
        "previous_job_title": contact["job_title"],
        "previous_buying_role": contact["buying_role"],
        "previous_email": contact["email"],
        "previous_phone": contact["phone"],
        "was_primary": contact.get("is_primary", False),
        "transferred_at": now_str,
        "transfer_reason": transfer_reason.strip() or "Chuyển sang công tác tại doanh nghiệp mới.",
        "sales_impact_note": sales_impact_note.strip() or f"Người liên hệ chuyển từ {old_cust_name} sang {new_cust_name}. Giữ mối quan hệ tốt để phát triển thương vụ mới."
    }

    # Đưa vào danh sách lịch sử của người liên hệ (mới nhất lên đầu)
    if "history" not in contact:
        contact["history"] = []
    contact["history"].insert(0, history_record)

    # 2. Xử lý đầu mối chính tại công ty cũ
    was_primary_at_old = contact.get("is_primary", False)
    if was_primary_at_old:
        # Tìm người thay thế làm đầu mối chính tại công ty cũ
        other_contacts_at_old = [
            c for cid, c in DB_CONTACTS.items()
            if c.get("customer_id") == old_customer_id and cid != contact_id
        ]
        if other_contacts_at_old:
            other_contacts_at_old[0]["is_primary"] = True

    # 3. Cập nhật thông tin sang công ty mới
    contact["customer_id"] = new_customer_id
    contact["job_title"] = new_job_title.strip()

    if new_email and new_email.strip():
        if not validate_email_address(new_email):
            raise ValueError(f"Email mới '{new_email}' không hợp lệ!")
        contact["email"] = new_email.strip().lower()

    if new_phone and new_phone.strip():
        if not validate_phone_number(new_phone):
            raise ValueError(f"Số điện thoại mới '{new_phone}' không hợp lệ!")
        contact["phone"] = re.sub(r"[\s.-]", "", new_phone.strip())

    if new_buying_role:
        if new_buying_role not in BUYING_ROLES:
            raise ValueError(f"Vai trò mua '{new_buying_role}' không hợp lệ!")
        contact["buying_role"] = new_buying_role

    # 4. Xử lý đầu mối chính tại công ty mới
    if is_primary_at_new_customer:
        for cid, cinfo in DB_CONTACTS.items():
            if cinfo.get("customer_id") == new_customer_id and cid != contact_id:
                cinfo["is_primary"] = False
        contact["is_primary"] = True
    else:
        # Nếu tại công ty mới chưa có ai là đầu mối chính -> tự động gán
        existing_primary = [
            c for cid, c in DB_CONTACTS.items()
            if c.get("customer_id") == new_customer_id and c.get("is_primary") and cid != contact_id
        ]
        contact["is_primary"] = (len(existing_primary) == 0)

    return copy.deepcopy(contact)


# ==============================================================================
# MA TRẬN QUYẾT ĐỊNH MUA HÀNG (BUYING CENTER MATRIX / POWER MAP)
# ==============================================================================
def get_buying_decision_matrix(customer_id: str) -> Dict[str, Any]:
    """
    Phân loại tất cả người liên hệ của một khách hàng vào 4 nhóm vai trò quyết định mua.
    Cung cấp bức tranh toàn cảnh (Power Map) kèm phân tích điểm mạnh, rủi ro thương vụ
    và cẩm nang chiến lược hành động cho Nhân viên kinh doanh.
    """
    cust = get_customer(customer_id)
    if not cust:
        raise ValueError(f"Khách hàng {customer_id} không tồn tại!")

    contacts = get_contacts_by_customer(customer_id)

    matrix = {
        "decision_makers": [],
        "influencers": [],
        "end_users": [],
        "blockers": []
    }

    role_key_mapping = {
        "decision_maker": "decision_makers",
        "influencer": "influencers",
        "end_user": "end_users",
        "blocker": "blockers"
    }

    for c in contacts:
        r = c.get("buying_role")
        key = role_key_mapping.get(r, "influencers")
        c_copy = copy.deepcopy(c)
        c_copy["role_meta"] = BUYING_ROLES.get(r)
        matrix[key].append(c_copy)

    # Đánh giá sức khỏe thương vụ (Deal Health Assessment)
    has_decision_maker = len(matrix["decision_makers"]) > 0
    has_blocker = len(matrix["blockers"]) > 0
    has_influencer = len(matrix["influencers"]) > 0
    has_end_user = len(matrix["end_users"]) > 0

    if has_decision_maker and not has_blocker and has_influencer:
        health_status = "Rất thuận lợi (Strong Momentum)"
        health_class = "health-positive"
        advice = "Đã tiếp cận được Người quyết định và có Người ảnh hưởng ủng hộ. Đẩy mạnh ký kết hợp đồng!"
    elif has_blocker and not has_decision_maker:
        health_status = "Nguy cơ cao (High Risk)"
        health_class = "health-danger"
        advice = "Thương vụ đang bị Người cản trở chặn đứng mà chưa tiếp cận được Người quyết định. Cần họp giải tỏa rào cản ngay!"
    elif has_blocker and has_decision_maker:
        health_status = "Cần thận trọng (Tension Point)"
        health_class = "health-warning"
        advice = "Đã có Người quyết định nhưng vẫn còn Người cản trở. Cần giải tỏa nỗi lo của Người cản trở để tránh bị lật kèo phút chót."
    elif not has_decision_maker:
        health_status = "Chưa hoàn thiện (Missing Economic Buyer)"
        health_class = "health-info"
        advice = "Chưa tiếp cận được Người quyết định ngân sách. Hãy nhờ Người ảnh hưởng giới thiệu lên cấp trên."
    else:
        health_status = "Bình thường"
        health_class = "health-neutral"
        advice = "Tiếp tục nuôi dưỡng quan hệ và làm rõ nhu cầu người dùng cuối."

    return {
        "customer": cust,
        "matrix": matrix,
        "total_contacts": len(contacts),
        "health_status": health_status,
        "health_class": health_class,
        "advice": advice,
        "role_definitions": BUYING_ROLES
    }
