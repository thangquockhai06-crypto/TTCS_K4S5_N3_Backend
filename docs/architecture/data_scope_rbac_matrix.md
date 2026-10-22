# Ma trận Phân quyền & Centralized Data Scope cho Phân hệ Công việc

| Vai trò (Role) | Data Scope | Quyền xem Task cá nhân | Quyền xem Task thành viên khác | Quyền xem Thống kê Trưởng nhóm |
|---|---|:---:|:---:|:---:|
| Nhân viên kinh doanh | OWN | Có (chỉ task của mình) | Không (HTTP 403 / Lọc CSDL) | Không (HTTP 403 Forbidden) |
| Trưởng nhóm kinh doanh | TEAM | Có (task của mình) | Có (task trong team) | Có (team của mình) |
| Giám đốc kinh doanh | ALL | Có | Có (toàn công ty) | Có (xem mọi team) |
| Quản trị viên hệ thống | ALL | Có | Có (toàn công ty) | Có (toàn bộ hệ thống) |
