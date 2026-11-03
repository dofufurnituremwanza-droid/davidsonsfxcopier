@echo off
title DAVIDSONSFX TRADING COPIER - SERVER
color 0b
echo ============================================================
echo      DAVIDSONSFX TRADING COPIER - CLOUD ENGINE
echo ============================================================
echo.

cd /d "%~dp0\.."

where py >nul 2>nul
if %errorlevel% equ 0 (
    echo [+] Starting DAVIDSONSFX Server via Python launcher...
    py backend\run_server.py
) else (
    echo [+] Starting DAVIDSONSFX Server via python...
    python backend\run_server.py
)

pause

