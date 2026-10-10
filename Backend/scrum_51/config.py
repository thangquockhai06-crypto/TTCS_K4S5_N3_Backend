"""
Cấu hình hệ thống - SCRUM-30 / SCRUM-51
Đề bài: "Là Nhân viên kinh doanh, tôi muốn nhận hoặc từ chối lead được phân,
có ràng buộc SLA phản hồi, để lead không nằm im ba ngày rồi nguội hẳn."
"""

# Các trạng thái của Lead
STATUS_PENDING_ALLOCATION = "PENDING_ALLOCATION"  # Hàng chờ phân bổ (mới hoặc bị từ chối quay lại)
STATUS_ASSIGNED = "ASSIGNED"                      # Đã phân bổ, chờ nhân viên nhận/từ chối
STATUS_IN_CARE = "IN_CARE"                        # Đang chăm sóc (Nhân viên đã bấm Nhận)
STATUS_CONTACTED = "CONTACTED"                    # Đã liên hệ khách hàng (Đạt cam kết SLA phản hồi)

STATUS_LABELS = {
    STATUS_PENDING_ALLOCATION: "Chờ phân bổ",
    STATUS_ASSIGNED: "Chờ tiếp nhận",
    STATUS_IN_CARE: "Đang chăm sóc",
    STATUS_CONTACTED: "Đã liên hệ"
}

STATUS_COLORS = {
    STATUS_PENDING_ALLOCATION: "#f59e0b",  # Vàng cam
    STATUS_ASSIGNED: "#3b82f6",            # Xanh dương
    STATUS_IN_CARE: "#8b5cf6",             # Tím
    STATUS_CONTACTED: "#10b981"            # Xanh lá
}

# Các vai trò trong hệ thống (RBAC)
ROLE_SALES_REP = "SALES_REP"          # Nhân viên kinh doanh
ROLE_TEAM_LEAD = "TEAM_LEAD"          # Trưởng nhóm kinh doanh
ROLE_DIRECTOR = "DIRECTOR"            # Giám đốc kinh doanh

# Cấu hình SLA phản hồi mặc định (giây)
# Trong môi trường thực tế: 3 ngày = 72 * 3600 = 259200s, hoặc 24h = 86400s
# Trong môi trường demo/kiểm thử: Mặc định 60 giây (1 phút) hoặc 30 giây để người chấm kiểm tra ngay lập tức
DEFAULT_SLA_SECONDS = 120             # 2 phút cho chế độ thực nghiệm
DEMO_FAST_SLA_SECONDS = 30           # 30 giây cho chế độ test siêu nhanh
PRODUCTION_SLA_SECONDS = 72 * 3600   # 3 ngày theo đề bài ("ba ngày rồi nguội hẳn")

# Danh sách lý do từ chối mẫu
DEFAULT_REJECTION_REASONS = [
    "Quá tải công việc, đang chăm sóc quá nhiều lead",
    "Sai chuyên môn hoặc không phụ trách nhóm ngành nghề này",
    "Khách hàng ở khu vực địa lý ngoài phạm vi phụ trách",
    "Trùng khách hàng cũ đang được đồng nghiệp khác theo dõi",
    "Số điện thoại / Thông tin liên hệ ban đầu không chính xác",
    "Khác (Nhập lý do chi tiết bên dưới)"
]
