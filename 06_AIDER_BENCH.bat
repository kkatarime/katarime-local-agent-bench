@echo off
rem Aider architect mode on the night-bench tasks (kk): Strata SC117, planner + editor on the same model.
rem Needs aider on PATH (py -3.12 -m pip install aider-install ^&^& aider-install). Result: logs\night\<time>\REPORT.md
rem   06_AIDER_BENCH.bat                  SC117, 256K context
rem   another model: powershell -File 05_night_bench.ps1 -Agent aider -Only "orca" -Tasks "B,C"
cd /d "%~dp0"
where aider >nul 2>nul || ( echo  aider is not installed: see README ^(Aider^) & pause & exit /b 1 )
echo  Other apps (Chrome, Edge etc.) will be closed in 15 seconds to free RAM. Ctrl+C to cancel.
timeout /t 15
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\05_night_bench.ps1" -Agent aider -Only "sc117" -Ctx 262144 -Tasks "B,C" %*
echo.
echo ===== finished. open logs\night\ (newest folder) REPORT.md =====
pause
