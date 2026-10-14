@echo off
title NexusCRM - Python Backend Server (Port 8000)
cd /d "%~dp0"

echo ===============================================================
echo   NexusCRM Backend Server - FastAPI
echo   Running at:    http://localhost:8000
echo   Swagger Docs:  http://localhost:8000/docs
echo ===============================================================

REM Kiem tra Python
set "PYTHON_CMD="
where python >nul 2>&1
if %ERRORLEVEL% equ 0 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 set "PYTHON_CMD=py"
)

if exist "%~dp0venv\Scripts\python.exe" set "PYTHON_CMD=%~dp0venv\Scripts\python.exe"
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"

if not defined PYTHON_CMD (
    echo [LOI] Khong tim thay Python trong he thong PATH!
    pause
    exit /b 1
)

REM Giai phong port 8000 neu bi chiem
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

%PYTHON_CMD% run.py
pause
