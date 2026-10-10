@echo off
chcp 65001 > nul
echo =================================================================
echo  HỆ THỐNG PHÂN BỔ LEAD TỰ ĐỘNG - TICKET SCRUM-30 / SCRUM-49
echo  Ngôn ngữ: Python 3 + Flask Framework
echo  Vai trò: Giám đốc kinh doanh & Trưởng nhóm
echo  Cam kết SLA: Phân bổ dưới 5 phút kể từ khi lead vào
echo =================================================================
echo.
echo [1/2] Kiểm tra thư viện Python...
py -m pip install -r requirements.txt
echo.
echo [2/2] Đang khởi chạy ứng dụng...
echo Mở trình duyệt tại: http://127.0.0.1:5000
echo.
start http://127.0.0.1:5000
py app.py
pause
