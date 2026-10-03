@echo off
chcp 65001 > NUL
title SCRUM-71 - Subtask Password Reset System

echo =========================================================================
echo  KÍCH HOẠT HỆ THỐNG ĐẶT LẠI MẬT KHẨU QUA EMAIL (SCRUM-71 / S1-03)
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
