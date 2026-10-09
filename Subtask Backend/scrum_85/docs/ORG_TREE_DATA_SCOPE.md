# Ma Trận Phân Quyền Cây Tổ Chức Và Phạm Vi Dữ Liệu (SCRUM-85)

## 1. Bốn cấp độ Data Scope
1. **PERSONAL (Cá nhân)**: Chỉ xem và thao tác trên bản ghi do chính mình làm chủ (`owner_id == current_user.id`).
2. **TEAM (Đội nhóm / Phòng ban)**: Trưởng nhóm được xem tất cả bản ghi thuộc về các thành viên trong đội.
3. **BRANCH (Chi nhánh)**: Giám đốc chi nhánh quản lý mọi phòng ban trực thuộc chi nhánh đó.
4. **GLOBAL (Toàn công ty)**: Ban giám đốc và Admin xem và tổng hợp dữ liệu toàn bộ tổ chức.
