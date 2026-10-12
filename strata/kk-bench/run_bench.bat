@echo off
chcp 65001 >nul
rem usage: run_bench.bat <config.json> <label>   close apps, start Strata without a browser, wait, bench
cd /d "C:\Users\kiyom\ai-models\Strata"
echo  Closing other apps in 5 seconds (Ctrl+C to cancel) ...
timeout /t 5
powershell -NoProfile -ExecutionPolicy Bypass -File "kk-close-apps.ps1"
start "Strata %~2 (close to stop)" cmd /k .venv\Scripts\python.exe serve\server.py --engine strata --config %~1 --port 8080
".venv\Scripts\python.exe" kk-bench\bench.py http://127.0.0.1:8080/v1 %~2
