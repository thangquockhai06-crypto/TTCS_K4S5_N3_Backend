@echo off
title NexusCRM - Python Backend Server (Port 8000)
cd /d "%~dp0"
echo ===============================================================
echo   NexusCRM Backend Server - FastAPI + MySQL
echo   Dang chay tai: http://localhost:8000
echo   Swagger Docs: http://localhost:8000/docs
echo ===============================================================
python run.py
pause
