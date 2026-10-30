@echo off
title Smart Garbage Detection System - Backend
echo ========================================================
echo Starting Smart Garbage Detection System Backend
echo ========================================================
cd /d "%~dp0\.."
set PYTHONPATH=%cd%\backend
call .\venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
