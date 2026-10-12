@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\00_diag.ps1"
echo.
echo ===== finished. log: logs\00_diag.log =====
timeout /t 8
