@echo off
chcp 65001 > nul
echo =================================================================
echo  DÒNG THỜI GIAN TƯƠNG TÁC KHÁCH HÀNG
echo  Mã Jira Ticket: ⚡ SCRUM-36 / ☑ SCRUM-57
echo  Ngôn ngữ: Python 3 + Flask Framework
echo  Vai trò: Chăm sóc khách hàng (Customer Service)
echo  Mục tiêu: Tiếp nhận khách từ đồng nghiệp, nắm bối cảnh trong 5 phút
echo =================================================================
echo.
echo [1/2] Đang kiểm tra ^& cài đặt thư viện phụ thuộc (Flask)...
py -m pip install -r requirements.txt
echo.
echo [2/2] Đang khởi chạy ứng dụng Flask...
echo Tự động mở trình duyệt tại: http://127.0.0.1:5057
echo.
start http://127.0.0.1:5057
py app.py
pause
