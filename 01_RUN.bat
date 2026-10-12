@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\01_run.ps1" %*
echo.
echo ===== finished. see logs\run.log =====
pause
