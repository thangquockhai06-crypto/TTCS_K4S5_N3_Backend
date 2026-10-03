@echo off
chcp 65001 > nul
title Hệ Thống Doanh Nghiệp - SCRUM-75
cls
echo =================================================================
echo   HỆ THỐNG QUẢN LÝ DOANH NGHIỆP - USER STORY SCRUM-75
echo   Báo lỗi 404 & 403 dùng chung giao diện - Không bị trang trắng
echo =================================================================
echo.
echo Đang khởi chạy máy chủ Python Flask...
echo Mở trình duyệt tại: http://127.0.0.1:5000
echo.
py app.py
pause
