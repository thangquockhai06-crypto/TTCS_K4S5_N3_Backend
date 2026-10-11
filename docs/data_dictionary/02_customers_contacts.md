# Từ Điển Dữ Liệu: Bảng Customers & Contacts

| Bảng | Tên Cột | Kiểu Dữ Liệu | Mô Tả |
|---|---|---|---|
| customers | id | INTEGER (PK) | Mã khách hàng duy nhất |
| customers | code | VARCHAR(50) | Mã định danh kinh doanh (CUST-XXXX) |
| customers | name | VARCHAR(255) | Tên công ty hoặc khách hàng |
| customers | tax_code | VARCHAR(50) | Mã số thuế doanh nghiệp |
| customers | parent_id | INTEGER (FK) | Khóa ngoại trỏ đến công ty mẹ |
| customers | status | VARCHAR(50) | Trạng thái: LEAD, PROSPECT, ACTIVE, INACTIVE |
| contacts | id | INTEGER (PK) | Mã người liên hệ |
| contacts | customer_id | INTEGER (FK) | Mã khách hàng trực thuộc |
| contacts | buying_role | VARCHAR(50) | Vai trò mua hàng (Decision Maker, Influencer,...) |
