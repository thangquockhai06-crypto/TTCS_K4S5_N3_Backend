@echo off
chcp 65001 > nul
echo =================================================================
echo  BÁO CÁO HIỆU QUẢ NGUỒN LEAD & CHIẾN DỊCH MARKETING - SCRUM-99
echo  Mã Jira Ticket: ⚡ SCRUM-30 / ☑ SCRUM-99
echo  Ngôn ngữ: Python 3 + Flask Framework
echo  Vai trò: Nhân viên Marketing (Marketing Specialist)
echo  Mục tiêu: Đánh giá tỷ lệ nhận, chuyển đổi cơ hội & xuất Excel
echo =================================================================
echo.
echo [1/2] Đang kiểm tra & cài đặt thư viện phụ thuộc (Flask, openpyxl)...
py -m pip install -r requirements.txt
echo.
echo [2/2] Đang khởi chạy ứng dụng Flask...
echo Tự động mở trình duyệt tại: http://127.0.0.1:5000
echo.
start http://127.0.0.1:5000
py app.py
pause
