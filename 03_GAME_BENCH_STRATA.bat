@echo off
rem Strata 2 models only (standard + Orca uncensored, thinking=medium), 1 hour cap each.
cd /d "%~dp0"
echo ============================================================
echo  LocalAgent game bench : Strata (2 models, up to 2 hours)
echo  Other apps (Chrome etc.) will be closed in 10 seconds to free RAM.
echo  Ctrl+C to cancel. Do not use the PC until "finished".
echo ============================================================
timeout /t 10
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\02_game_bench.ps1" -Only "strata-qwen38-flash-next_medium,strata-orca-uncensored_medium" %*
echo.
echo ===== finished. see logs\bench\bench.log =====
pause
