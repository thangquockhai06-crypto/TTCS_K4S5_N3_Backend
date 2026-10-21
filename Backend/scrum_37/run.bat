@echo off
chcp 65001 >nul
title AutoLead CRM - SCRUM-37: Quan Ly Nhieu Phien Ban Bao Gia

echo ======================================================================
echo   AUTOLEAD CRM - HỆ THỐNG QUẢN LÝ NHIỀU PHIÊN BẢN BÁO GIÁ
echo   Ticket: SCRUM-35 / SCRUM-37 (Subtasks: SCRUM-234 FE ^& SCRUM-235 BE)
echo ======================================================================
echo.

echo [1/3] Đang kiểm tra môi trường Python...
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python trên máy. Vui lòng cài đặt Python 3.10+
    pause
    exit /b
)

echo [2/3] Đang tự động mở trình duyệt tại: http://127.0.0.1:5003
start "" http://127.0.0.1:5003

echo [3/3] Đang khởi chạy máy chủ Flask Web Server trên cổng 5003...
echo Nhấn Ctrl+C để dừng máy chủ.
echo.
py app.py
pause
