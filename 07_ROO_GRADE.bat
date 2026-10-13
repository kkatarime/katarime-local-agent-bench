@echo off
rem Roo Code test, step 2 (kk): grade the folders and compare with SC117 (built-in loop) and Aider.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\07_roo.ps1" -Step grade %*
pause
