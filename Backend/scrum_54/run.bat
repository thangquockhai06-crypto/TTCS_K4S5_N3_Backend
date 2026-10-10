@echo off
chcp 65001 > nul
echo =================================================================
echo  HỆ THỐNG CHUYỂN ĐỔI LEAD CRM (1-CLICK CONVERSION) - SCRUM-54
echo  Mã Jira Ticket: ⚡ SCRUM-30 / ☑ SCRUM-54
echo  Ngôn ngữ: Python 3 + Flask Framework
echo  Vai trò: Nhân viên kinh doanh (Sales Representative)
echo =================================================================
echo.
echo [1/2] Đang kiểm tra & cài đặt thư viện phụ thuộc...
py -m pip install -r requirements.txt
echo.
echo [2/2] Đang khởi chạy ứng dụng Flask...
echo Tự động mở trình duyệt tại: http://127.0.0.1:5000
echo.
start http://127.0.0.1:5000
py app.py
pause
