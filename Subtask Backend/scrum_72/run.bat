@echo off
chcp 65001 > NUL
title SCRUM-72 - Subtask Change Password System

echo =========================================================================
echo  KÍCH HOẠT HỆ THỐNG ĐỔI MẬT KHẨU TÀI KHOẢN (SCRUM-72 / S1-04)
echo =========================================================================
echo.

cd /d %~dp0

if exist ..\..\server\venv\Scripts\python.exe (
    set PYTHON_CMD=..\..\server\venv\Scripts\python.exe
) else (
    set PYTHON_CMD=python
)

echo [SERVER] Đang khởi chạy Subtask Backend Flask App...
%PYTHON_CMD% app.py

pause
