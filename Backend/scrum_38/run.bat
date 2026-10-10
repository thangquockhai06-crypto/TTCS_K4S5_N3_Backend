@echo off
chcp 65001 >nul
title AutoLead CRM - SCRUM-38: Chuyen Bao Gia Thanh Hop Dong

echo ======================================================================
echo   AUTOLEAD CRM - CHUYỂN BÁO GIÁ THÀNH HỢP ĐỒNG (SCRUM-38)
echo   Ticket: SCRUM-35 / SCRUM-38 (Subtasks: SCRUM-236 FE ^& SCRUM-237 BE)
echo   User Story: Là Kế toán, tôi muốn chuyển một báo giá được chấp nhận
echo               thành hợp đồng, để số liệu hợp đồng khớp báo giá
echo               mà không phải gõ lại.
echo ======================================================================
echo.

echo [1/3] Đang kiểm tra môi trường Python...
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python trên máy. Vui lòng cài đặt Python 3.10+
    pause
    exit /b
)

echo [2/3] Đang tự động mở trình duyệt tại: http://127.0.0.1:5004
start "" http://127.0.0.1:5004

echo [3/3] Đang khởi chạy máy chủ Flask Web Server trên cổng 5004...
echo Nhấn Ctrl+C để dừng máy chủ.
echo.
py app.py
pause
