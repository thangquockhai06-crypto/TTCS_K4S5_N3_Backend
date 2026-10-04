@echo off
chcp 65001 >nul
title AutoLead CRM - SCRUM-33: Duyet Bao Gia Theo Chiet Khau

echo ======================================================================
echo   AUTOLEAD CRM - HỆ THỐNG DUYỆT BÁO GIÁ THEO MỨC CHIẾT KHẤU
echo   Ticket: SCRUM-35 / SCRUM-33 (Subtasks: SCRUM-232 FE ^& SCRUM-233 BE)
echo ======================================================================
echo.

echo [1/3] Đang kiểm tra môi trường Python...
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python trên máy. Vui lòng cài đặt Python 3.10+
    pause
    exit /b
)

echo [2/3] Đang tự động mở trình duyệt tại: http://127.0.0.1:5002
start "" http://127.0.0.1:5002

echo [3/3] Đang khởi chạy máy chủ Flask Web Server trên cổng 5002...
echo Nhấn Ctrl+C để dừng máy chủ.
echo.
py app.py
pause
