@echo off
chcp 65001 >nul
setlocal
title Strata update (kk)
cd /d "C:\Users\kiyom\ai-models\Strata"
set LOG=C:\Users\kiyom\ai-models\Strata\kk-bench\update-log.txt
echo ==== Strata update %date% %time% ==== > "%LOG%"
echo [1/4] Stopping running Strata ...
powershell -NoProfile -Command "Get-Process strata,strata-vision -EA SilentlyContinue | Stop-Process -Force; Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -like '*server.py*--engine strata*' } | %% { Stop-Process -Id $_.ProcessId -Force }; Get-NetTCPConnection -LocalPort 8080 -State Listen -EA SilentlyContinue | %% { Stop-Process -Id $_.OwningProcess -Force }"
echo --- before >> "%LOG%"
type engine\BUILD.json >> "%LOG%" 2>&1
git log -1 --format="%%h %%ci %%s" >> "%LOG%" 2>&1
echo [2/4] git fetch / backup branch / checkout ...
git fetch origin >> "%LOG%" 2>&1 || goto :fail
git branch pre-cleanup-backup >> "%LOG%" 2>&1
git checkout -B main origin/main >> "%LOG%" 2>&1 || goto :fail
git log -1 --format="%%h %%ci %%s" >> "%LOG%" 2>&1
echo [3/4] UPDATE.bat (engine and settings) ... When it says "Press any key", press a key.
call UPDATE.bat
echo --- after >> "%LOG%"
type engine\BUILD.json >> "%LOG%" 2>&1
echo [4/4] Done. >> "%LOG%"
echo.
echo  Update finished. Tell Claude "更新できた".
pause
exit /b 0
:fail
echo  [x] git step failed. See kk-bench\update-log.txt and tell Claude. >> "%LOG%"
echo.
echo  [x] git step failed. Tell Claude "更新でエラー".
pause
exit /b 1
