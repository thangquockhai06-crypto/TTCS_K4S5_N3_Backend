@echo off
chcp 65001 > nul
title SCRUM-85: He Thong Khai Bao Co Cau To Chuc Kinh Doanh va Pham Vi Du Lieu
echo ====================================================================
echo  HỆ THỐNG KHAI BÁO CƠ CẤU TỔ CHỨC & PHẠM VI DỮ LIỆU (SCRUM-85)
echo  ⚡ SCRUM-83 / ☑ SCRUM-85
echo  Tiêu chí: Cây tổ chức + Trưởng nhóm + 1 NV/1 Nhóm + Data Scope + Khu vực
echo ====================================================================
echo.
echo Đang kiểm tra thư viện Flask...
py -c "import flask" 2>nul
if %errorlevel% neq 0 (
    echo Chưa cài đặt Flask, đang tiến hành cài đặt...
    py -m pip install flask
)

echo.
echo Khởi chạy máy chủ Flask...
echo Mở trình duyệt tại địa chỉ: http://127.0.0.1:5000
echo Nhấn Ctrl+C để dừng máy chủ.
echo.
py app.py
pause
