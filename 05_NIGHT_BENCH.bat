@echo off
rem Overnight bench (kk): every Strata model (SC117 Swift, Orca, SC117, standard) one after another,
rem up to 2 hours each: long context, multi-file work, things to build. Result: logs\night\<time>\REPORT.md
rem   05_NIGHT_BENCH.bat -Only "orca,sc117-swift"     05_NIGHT_BENCH.bat -LimitSec 5400 -Ctx 32768
cd /d "%~dp0"
echo ============================================================
echo  NIGHT BENCH : all Strata models, up to 2 hours each (about 8 hours)
echo  Other apps (Chrome, Edge etc.) will be closed in 15 seconds to free RAM.
echo  Save your work. Ctrl+C to cancel. Do not use the PC until "finished".
echo ============================================================
timeout /t 15
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\05_night_bench.ps1" %*
echo.
echo ===== finished. open logs\night\ (newest folder) REPORT.md =====
pause
