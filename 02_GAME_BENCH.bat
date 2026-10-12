@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\02_game_bench.ps1" %*
echo.
echo ===== finished. see logs\bench\bench.log =====
pause
