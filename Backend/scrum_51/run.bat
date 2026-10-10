@echo off
chcp 65001 > nul
echo =================================================================
echo  HỆ THỐNG TIẾP NHẬN LEAD & GIÁM SÁT SLA PHẢN HỒI - SCRUM-51
echo  Ticket Jira: SCRUM-30 / SCRUM-51
echo  Ngôn ngữ: Python 3 + Flask Framework
echo  Vai trò: Nhân viên kinh doanh & Trưởng nhóm
echo  Cam kết SLA: Không để lead nằm im quá 3 ngày rồi nguội hẳn
echo =================================================================
echo.
echo [1/2] Kiểm tra & cài đặt thư viện phụ thuộc...
py -m pip install -r requirements.txt
echo.
echo [2/2] Đang khởi chạy ứng dụng Flask...
echo Tự động mở trình duyệt tại: http://127.0.0.1:5000
echo.
start http://127.0.0.1:5000
py app.py
pause
