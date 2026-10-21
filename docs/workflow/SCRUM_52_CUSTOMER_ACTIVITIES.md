# SCRUM-52: Ghi nhan hoat dong tuong tac khach hang

## 1. Mo ta User Story
La Nhan vien kinh doanh, toi muon ghi nhan mot hoat dong voi khach hang, de lich su trao doi khong nam trong hop thu ca nhan cua rieng toi.

## 2. Nghiep vu chinh
- **Loai hoat dong ho tro**: Cuoc goi (call), Email (email), Cuoc hop (meeting), Ghi chu tuong tac (note).
- **Thong tin luu tru**:
  - `customer_id`: Lien ket toi khach hang tuong ung.
  - `activity_type`: Phan loai hinh thuc tuong tac.
  - `subject` & `description`: Chu de va noi dung chi tiet cuoc trao doi.
  - `performed_at`: Thoi diem dien ra tuong tac.
  - `user_id`: Nguoi thuc hien (Sales Rep/CS).
- **Luu vet lich su**: Tich hop dong thoi gian vao Customer 360 Timeline va luu audit log.
