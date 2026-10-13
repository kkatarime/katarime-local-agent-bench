@echo off
rem Roo Code test, step 1 (kk): make the 10 task folders in %USERPROFILE%\roo-bench\tasks.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\07_roo.ps1" -Step prepare %*
pause
