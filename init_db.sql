-- =====================================================================
-- CSDL CHO DỰ ÁN NEXUSCRM (TTCS_K4S5_N3)
-- Chạy script này trong MySQL Workbench
-- =====================================================================

CREATE DATABASE IF NOT EXISTS nexuscrm_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE nexuscrm_db;

-- 1. BẢNG TÀI KHOẢN NGƯỜI DÙNG / NHÂN VIÊN (SCRUM-32 / SCRUM-101)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'Super Admin',
    title VARCHAR(150) DEFAULT 'Quản trị viên hệ thống',
    department VARCHAR(150) DEFAULT 'Ban Quản Trị & Vận Hành Doanh Thu',
    avatar_url TEXT,
    avatar_thumbnail_url TEXT,
    workspace_name VARCHAR(150) DEFAULT 'NexusCRM Enterprise VN',
    team_id VARCHAR(50) DEFAULT NULL,
    data_scope VARCHAR(20) DEFAULT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    failed_attempts INT NOT NULL DEFAULT 0,
    lockout_until DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_email (email),
    INDEX idx_user_team (team_id),
    INDEX idx_user_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. BẢNG QUẢN LÝ PHIÊN & REFRESH TOKEN (SCRUM-34 / SCRUM-103)
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    token TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. BẢNG KHÁCH HÀNG (CUSTOMERS)
CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR(36) PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(120) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    company VARCHAR(150) DEFAULT '',
    tax_code VARCHAR(50) DEFAULT NULL,
    status ENUM('lead', 'prospect', 'active', 'inactive') NOT NULL DEFAULT 'lead',
    health_score INT NOT NULL DEFAULT 85,
    assigned_user_id VARCHAR(36) DEFAULT NULL,
    avatar_url TEXT,
    parent_id VARCHAR(36) DEFAULT NULL,
    industry VARCHAR(50) DEFAULT NULL,
    company_size VARCHAR(30) DEFAULT NULL,
    region VARCHAR(100) DEFAULT NULL,
    address VARCHAR(255) DEFAULT NULL,
    website VARCHAR(255) DEFAULT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    merged_into_id VARCHAR(36) DEFAULT NULL,
    normalized_name VARCHAR(255) NOT NULL DEFAULT '',
    normalized_tax_code VARCHAR(50) NOT NULL DEFAULT '',
    normalized_phone VARCHAR(30) NOT NULL DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customer_name (normalized_name),
    INDEX idx_customer_tax_code (normalized_tax_code),
    INDEX idx_customer_phone (normalized_phone),
    INDEX idx_customer_industry (industry),
    INDEX idx_customer_company_size (company_size),
    INDEX idx_customer_region (region),
    INDEX idx_customer_is_deleted (is_deleted),
    INDEX idx_customer_parent (parent_id),
    INDEX idx_customer_merged_into (merged_into_id),
    FOREIGN KEY (assigned_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (parent_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (merged_into_id) REFERENCES customers(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS customer_contacts (
    id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    normalized_phone VARCHAR(30) NOT NULL,
    email VARCHAR(120) DEFAULT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_customer_contact_customer (customer_id),
    INDEX idx_customer_contact_phone (normalized_phone),
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS saved_filters (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    filter_definition JSON NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_saved_filter_user_name (user_id, name),
    INDEX idx_saved_filter_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. BẢNG CƠ HỘI BÁN HÀNG (DEALS / KANBAN PIPELINE)
CREATE TABLE IF NOT EXISTS deals (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    value DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    stage ENUM('lead', 'contact', 'proposal', 'negotiation', 'won', 'lost') NOT NULL DEFAULT 'lead',
    probability INT NOT NULL DEFAULT 20,
    customer_id VARCHAR(36) NOT NULL,
    owner_id VARCHAR(36) NOT NULL,
    expected_close_date DATE DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. BẢNG NHẬT KÝ HOẠT ĐỘNG (ACTIVITIES)
CREATE TABLE IF NOT EXISTS activities (
    id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    type ENUM('call', 'meeting', 'email', 'deal_change', 'status_change') NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. BẢNG GHI CHÚ KHÁCH HÀNG (NOTES)
CREATE TABLE IF NOT EXISTS notes (
    id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    author_id VARCHAR(36) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. CATALOG / PRICE BOOK
CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'Catalog',
    unit VARCHAR(50) NOT NULL DEFAULT 'unit',
    selling_price DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    cost_price DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    type VARCHAR(30) NOT NULL DEFAULT 'ONE_TIME_PRODUCT',
    unit_of_measure VARCHAR(50) NOT NULL DEFAULT 'unit',
    list_price DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    floor_price DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    currency VARCHAR(3) NOT NULL DEFAULT 'VND',
    discontinued_at DATETIME DEFAULT NULL,
    created_by VARCHAR(36) DEFAULT NULL,
    updated_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CHECK (list_price >= 0),
    CHECK (floor_price >= 0),
    CHECK (cost_price >= 0),
    CHECK (floor_price <= list_price),
    INDEX idx_product_code (code),
    INDEX idx_product_name (name),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. BẢNG BÁO GIÁ (QUOTATIONS)
CREATE TABLE IF NOT EXISTS quotations (
    id VARCHAR(36) PRIMARY KEY,
    quote_number VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    customer_id VARCHAR(36) NOT NULL,
    owner_id VARCHAR(36) NOT NULL,
    total_amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    discount_approval_required BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    valid_until DATE DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_quote_number (quote_number),
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotation_lines (
    id VARCHAR(36) PRIMARY KEY,
    quotation_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    unit_price DECIMAL(15, 2) NOT NULL,
    list_price_snapshot DECIMAL(15, 2) NOT NULL,
    floor_price_snapshot DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'VND',
    discount_approval_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    INDEX idx_quotation_line_quote (quotation_id),
    INDEX idx_quotation_line_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. BẢNG VAI TRÒ (ROLES) & LIÊN KẾT (USER_ROLES)
CREATE TABLE IF NOT EXISTS roles (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_role_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_roles (
    user_id VARCHAR(36) NOT NULL,
    role_id VARCHAR(36) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. BẢNG NHÓM KINH DOANH (TEAMS) & LIÊN KẾT (USER_TEAMS)
CREATE TABLE IF NOT EXISTS teams (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_team_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_teams (
    user_id VARCHAR(36) NOT NULL,
    team_id VARCHAR(36) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, team_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. BẢNG NHẬT KÝ THAO TÁC HỆ THỐNG (AUDIT_LOGS)
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT DEFAULT NULL,
    performed_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (performed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. BẢNG DANH MỤC LÝ DO THẮNG / THUA (WIN_LOSS_REASONS - S2-10 / SCRUM-89)
CREATE TABLE IF NOT EXISTS win_loss_reasons (
    id VARCHAR(36) PRIMARY KEY,
    result_type VARCHAR(10) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    reason VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    usage_count INT NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_reason_result_type (result_type),
    INDEX idx_reason_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. BẢNG ĐỐI THỦ CẠNH TRANH (COMPETITORS - S2-10 / SCRUM-89)
CREATE TABLE IF NOT EXISTS competitors (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    website VARCHAR(255) DEFAULT NULL,
    pricing_tier VARCHAR(100) DEFAULT 'Trung cấp',
    strengths TEXT DEFAULT NULL,
    weaknesses TEXT DEFAULT NULL,
    win_rate DECIMAL(5, 2) NOT NULL DEFAULT 50.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_competitor_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- DỮ LIỆU BAN ĐẦU: Tài khoản Admin mặc định & Danh mục cơ sở
-- Mật khẩu mặc định: Admin@2026 (bcrypt hash: $2b$12$N2aF4GgA3Wl5O80S47ZZeepB5G3WJ1dM43hCgXzL9s3fKkYtTz8S2)
-- =====================================================================
INSERT INTO users (id, email, password_hash, full_name, role, title, department, avatar_url, workspace_name, failed_attempts, lockout_until)
VALUES (
    'usr-admin-01',
    'admin@nexuscrm.vn',
    '$2b$12$4s2.s324QJ0PqP7x5b1QG.9nFfW3WdDqJ4wJ3n4D7n8s9d0a1b2c3', -- Được cập nhật tự động khi chạy seed.py
    'Quản Trị Viên Hệ Thống',
    'Super Admin',
    'Quản trị viên cấp cao (System Admin)',
    'Ban Quản Trị & Vận Hành Doanh Thu',
    'https://api.dicebear.com/7.x/initials/svg?seed=QuanTriVien',
    'NexusCRM Enterprise VN',
    0,
    NULL
) ON DUPLICATE KEY UPDATE full_name = VALUES(full_name);

-- Nạp lý do Thắng / Thua mặc định
INSERT INTO win_loss_reasons (id, result_type, code, reason, description, is_active, usage_count)
VALUES
    ('rs-won-01', 'WON', 'PRICE_COMPETITIVE', 'Chính sách giá & Chiết khấu cạnh tranh vượt trội', 'Báo giá tốt hơn đối thủ từ 10-15% kèm chính sách trả góp linh hoạt', 1, 48),
    ('rs-won-02', 'WON', 'FEATURE_RICH', 'Tính năng phân quyền & Tùy biến đa cấp đáp ứng 100% nghiệp vụ', 'Khách hàng đánh giá rất cao phân hệ trường tùy chỉnh và sơ đồ cây phòng ban', 1, 36),
    ('rs-won-03', 'WON', 'SUPPORT_EXCELLENT', 'Dịch vụ Onboarding & Hỗ trợ kỹ thuật 24/7 tận tâm', 'Cam kết SLA phản hồi dưới 15 phút và hỗ trợ trực tiếp tại doanh nghiệp', 1, 24),
    ('rs-lost-01', 'LOST', 'BUDGET_CUT', 'Khách hàng cắt giảm ngân sách đầu tư CNTT năm nay', 'Dự án bị hoãn sang quý sau do biến động kinh doanh nội bộ khách hàng', 1, 19),
    ('rs-lost-02', 'LOST', 'CHOSE_COMPETITOR', 'Khách hàng chọn đối thủ có giá thành thấp hơn', 'Khách hàng chấp nhận giải pháp ít tính năng hơn để tiết kiệm chi phí ban đầu', 1, 14),
    ('rs-lost-03', 'LOST', 'INTERNAL_BUILD', 'Khách hàng quyết định tự xây dựng phần mềm nội bộ (In-house)', 'Đội ngũ IT nội bộ của khách hàng tiếp quản dự án', 1, 5)
ON DUPLICATE KEY UPDATE reason = VALUES(reason);

-- Nạp đối thủ cạnh tranh mặc định
INSERT INTO competitors (id, name, website, pricing_tier, strengths, weaknesses, win_rate, is_active)
VALUES
    ('comp-01', 'Salesforce CRM Enterprise', 'https://www.salesforce.com', 'Rất cao (2.500.000đ/user/tháng)', 'Thương hiệu toàn cầu, hệ sinh thái AppExchange phong phú', 'Chi phí triển khai cực kỳ đắt đỏ, giao diện tiếng Anh khó sử dụng', 68.00, 1),
    ('comp-02', 'HubSpot Sales Hub', 'https://www.hubspot.com', 'Trung bình - Cao (1.200.000đ/user/tháng)', 'Marketing Automation mạnh mẽ, giao diện trực quan', 'Tính năng phân quyền sâu và quản lý giá sàn còn hạn chế', 74.00, 1),
    ('comp-03', 'Zoho CRM Plus', 'https://www.zoho.com', 'Trung bình (650.000đ/user/tháng)', 'Nhiều phân hệ tích hợp, chi phí bản quyền ban đầu cạnh tranh', 'Tốc độ tải chậm tại Việt Nam, quy trình tùy biến phễu phức tạp', 82.00, 1)
ON DUPLICATE KEY UPDATE pricing_tier = VALUES(pricing_tier);
