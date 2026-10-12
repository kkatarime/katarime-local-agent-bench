@echo off
chcp 65001 >nul
setlocal
title Strata bench v2 (kk)
cd /d "C:\Users\kiyom\ai-models\Strata"
set PY=C:\Users\kiyom\ai-models\Strata\.venv\Scripts\python.exe
set PYTHONIOENCODING=utf-8
set LOG=C:\Users\kiyom\ai-models\Strata\kk-bench\bench2-console.txt
echo ============================================================
echo  Strata performance test (2 models, about 40-60 min)
echo  Do not use the PC until it says "ALL DONE".
echo  Other apps will be closed in 10 seconds (Ctrl+C to cancel).
echo ============================================================
timeout /t 10
powershell -NoProfile -ExecutionPolicy Bypass -File "kk-close-apps.ps1"
echo ==== bench2 %date% %time% ==== >> "%LOG%"

call :one "strata-iq3_xxs.json" strata
call :one "kk-orca\orca-iq3_xxs.json" orca

echo ==== ALL DONE %date% %time% ==== >> "%LOG%"
echo.
echo ============================================================
echo  ALL DONE. Tell Claude "テスト終わった".
echo ============================================================
pause
exit /b 0

:one
echo.
echo ===== %~2 : starting Strata (%~1) =====
call :stop
start "Strata %~2 (bench)" /min cmd /c ""%PY%" serve\server.py --engine strata --config %~1 --port 8080"
"%PY%" kk-bench\bench2.py %~2
call :stop
timeout /t 20 /nobreak >nul
exit /b 0

:stop
powershell -NoProfile -Command "Get-Process strata,strata-vision -EA SilentlyContinue | Stop-Process -Force; Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -like '*server.py*--engine strata*' } | %% { Stop-Process -Id $_.ProcessId -Force }; Get-NetTCPConnection -LocalPort 8080 -State Listen -EA SilentlyContinue | %% { Stop-Process -Id $_.OwningProcess -Force }"
exit /b 0
