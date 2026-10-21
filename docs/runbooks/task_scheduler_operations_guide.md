# Hướng dẫn Vận hành Background Task Scheduler (Runbook)

## Kiểm tra Trạng thái Scheduler
1. Đăng nhập hệ thống giám sát hoặc xem logs của backend:
   ```bash
   grep "[SCHEDULER]" app.log
   ```
2. Tần suất quét mặc định: 60 giây/lần.
3. Khi phát hiện công việc quá hạn hoặc chạm mốc nhắc việc, log hiển thị:
   `[SCHEDULER SCAN] Quét hoàn tất: X task quá hạn, Y task được nhắc nhở.`

## Xử lý sự cố khi Scheduler bị dừng
- Khởi động lại service hoặc container backend:
  `docker compose restart backend`
- Kiểm tra kết nối CSDL và tài khoản kết nối trong file `.env`.
