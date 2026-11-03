@echo off
title DAVIDSONSFX TRADING COPIER - SERVER
color 0b
echo ============================================================
echo      DAVIDSONSFX TRADING COPIER - CLOUD ENGINE
echo ============================================================
echo.

cd /d "%~dp0\.."

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    python backend\run_server.py
) else (
    echo [!] Virtual environment not detected. Running with system python...
    python backend\run_server.py
)

pause

