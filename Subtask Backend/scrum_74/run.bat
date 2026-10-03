@echo off
chcp 65001 > nul
title HỆ THỐNG MENU PHÂN QUYỀN RBAC - SCRUM-74
color 0B

echo =================================================================
echo   HỆ THỐNG MENU ĐIỀU HƯỚNG PHÂN QUYỀN (RBAC NAVIGATION SYSTEM)
echo   Mã User Story: SCRUM-69 / SCRUM-74
echo =================================================================
echo.
echo   [1] Cài đặt thư viện Flask (nếu chưa cài)
py -m pip install flask > nul 2>&1
echo   [2] Khởi chạy máy chủ Web...
echo.
echo   Mở trình duyệt truy cập: http://127.0.0.1:5000
echo   Bấm Ctrl + C trong cửa sổ này để dừng máy chủ.
echo =================================================================
echo.

py app.py
pause
