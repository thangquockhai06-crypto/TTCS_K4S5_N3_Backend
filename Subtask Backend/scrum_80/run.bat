@echo off
chcp 65001 > nul
title SCRUM-80: He Thong Ho So Ca Nhan va Chu Ky Email Bao Gia
echo ====================================================================
echo  HỆ THỐNG HỒ SƠ CÁ NHÂN & CHỮ KÝ EMAIL BÁO GIÁ (SCRUM-80)
echo  ⚡ SCRUM-69 / ☑ SCRUM-80
echo  Tiêu chí: Sửa Tên, SĐT, Chữ ký + Khóa Email, Nhóm, Vai trò + Validate SĐT VN
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
