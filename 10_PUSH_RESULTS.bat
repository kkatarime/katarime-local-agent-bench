@echo off
rem Push the newest bench results (logs\night\<newest>) to GitHub as results\<run>\ (kk).
rem   10_PUSH_RESULTS.bat -Dir "logs\night\20261014-0342"     a given run
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\push_results.ps1" %*
pause
