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
    status ENUM('lead', 'prospect', 'active', 'inactive') NOT NULL DEFAULT 'lead',
    health_score INT NOT NULL DEFAULT 85,
    assigned_user_id VARCHAR(36) DEFAULT NULL,
    avatar_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_user_id) REFERENCES users(id) ON DELETE SET NULL
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
    status VARCHAR(10) NOT NULL DEFAULT 'OPEN',
    closed_at DATETIME DEFAULT NULL,
    closed_by VARCHAR(36) DEFAULT NULL,
    actual_value DECIMAL(15, 2) DEFAULT NULL,
    signed_date DATE DEFAULT NULL,
    lost_reason_id VARCHAR(36) DEFAULT NULL,
    lost_reason_note TEXT DEFAULT NULL,
    competitor_id VARCHAR(36) DEFAULT NULL,
    reopened_at DATETIME DEFAULT NULL,
    reopened_by VARCHAR(36) DEFAULT NULL,
    reopen_reason TEXT DEFAULT NULL,
    last_open_stage VARCHAR(30) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT ck_deal_status_valid CHECK (status IN ('OPEN', 'WON', 'LOST')),
    CONSTRAINT ck_deal_outcome_fields CHECK (
        (status = 'OPEN' AND actual_value IS NULL AND signed_date IS NULL AND lost_reason_id IS NULL
            AND lost_reason_note IS NULL AND competitor_id IS NULL AND closed_at IS NULL AND closed_by IS NULL)
        OR (status = 'WON' AND actual_value IS NOT NULL AND actual_value > 0 AND signed_date IS NOT NULL
            AND lost_reason_id IS NULL AND lost_reason_note IS NULL AND competitor_id IS NULL
            AND closed_at IS NOT NULL AND closed_by IS NOT NULL)
        OR (status = 'LOST' AND actual_value IS NULL AND signed_date IS NULL AND lost_reason_id IS NOT NULL
            AND closed_at IS NOT NULL AND closed_by IS NOT NULL)
    ),
    INDEX idx_deal_status (status),
    INDEX idx_deal_stage (stage),
    INDEX idx_deal_value (value),
    INDEX idx_deal_expected_close (expected_close_date),
    INDEX idx_deal_owner (owner_id),
    INDEX idx_deal_customer (customer_id),
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reopened_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.1 BẢNG LIÊN KẾT DEAL - PRODUCT (SCRUM-206)
CREATE TABLE IF NOT EXISTS deal_products (
    deal_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    PRIMARY KEY (deal_id, product_id),
    INDEX idx_deal_products_deal (deal_id),
    INDEX idx_deal_products_product (product_id),
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.2 BẢNG BỘ LỌC CÁ NHÂN CHO DEALS (SAVED_DEAL_FILTERS - SCRUM-206)
CREATE TABLE IF NOT EXISTS saved_deal_filters (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(150) NOT NULL,
    filter_criteria JSON NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_saved_deal_filter_user_name (user_id, name),
    INDEX idx_saved_deal_filter_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.3 BẢNG THÀNH VIÊN PHỐI HỢP CƠ HỘI BÁN HÀNG (DEAL_MEMBERS - SCRUM-207)
CREATE TABLE IF NOT EXISTS deal_members (
    id VARCHAR(36) PRIMARY KEY,
    deal_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    role_in_deal VARCHAR(50) NOT NULL DEFAULT 'COLLABORATOR',
    added_by VARCHAR(36) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_deal_member (deal_id, user_id),
    INDEX idx_deal_member_deal (deal_id),
    INDEX idx_deal_member_user (user_id),
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.4 BẢNG NHẬT KÝ THAY ĐỔI CƠ HỘI (DEAL_HISTORIES - SCRUM-207)
CREATE TABLE IF NOT EXISTS deal_histories (
    id VARCHAR(36) PRIMARY KEY,
    deal_id VARCHAR(36) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(36) DEFAULT NULL,
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_deal_histories_deal (deal_id),
    INDEX idx_deal_histories_field (field_name),
    INDEX idx_deal_histories_changed_at (changed_at),
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS deal_outcome_history (
    id VARCHAR(36) PRIMARY KEY,
    deal_id VARCHAR(36) NOT NULL,
    action VARCHAR(20) NOT NULL,
    outcome VARCHAR(10) NOT NULL,
    previous_status VARCHAR(10) NOT NULL,
    resulting_status VARCHAR(10) NOT NULL,
    previous_stage VARCHAR(30) DEFAULT NULL,
    resulting_stage VARCHAR(30) DEFAULT NULL,
    actor_id VARCHAR(36) DEFAULT NULL,
    event_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME DEFAULT NULL,
    closed_by VARCHAR(36) DEFAULT NULL,
    actual_value DECIMAL(15, 2) DEFAULT NULL,
    signed_date DATE DEFAULT NULL,
    lost_reason_id VARCHAR(36) DEFAULT NULL,
    lost_reason_note TEXT DEFAULT NULL,
    competitor_id VARCHAR(36) DEFAULT NULL,
    reopen_reason TEXT DEFAULT NULL,
    INDEX idx_deal_outcome_history_deal (deal_id),
    INDEX idx_deal_outcome_history_event (event_at),
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
    FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (closed_by) REFERENCES users(id) ON DELETE SET NULL
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

-- 7. BẢNG BÁO GIÁ (QUOTATIONS)
CREATE TABLE IF NOT EXISTS quotations (
    id VARCHAR(36) PRIMARY KEY,
    quote_number VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    customer_id VARCHAR(36) NOT NULL,
    owner_id VARCHAR(36) NOT NULL,
    total_amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    valid_until DATE DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_quote_number (quote_number),
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
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

-- =====================================================================
-- DỮ LIỆU BAN ĐẦU: Tài khoản Admin mặc định
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
