# Cẩm Nang Xử Lý Sự Cố Thường Gặp (Troubleshooting Guide)

1. **Lỗi Port 8000 đã bị chiếm dụng (Address already in use)**
   - Giải pháp: Chạy `netstat -ano | findstr :8000` và kill tiến trình qua `taskkill /PID <PID> /F`.
2. **Lỗi SQLite Database Locked**
   - Đảm bảo đóng kết nối session đúng cách qua context manager `with SessionLocal() as db:`.
3. **Lỗi JWT Token Expired**
   - Đăng nhập lại để nhận access token mới hoặc gọi endpoint refresh token.
