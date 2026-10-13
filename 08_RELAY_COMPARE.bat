@echo off
rem Relay compare (kk): SC117 at 256K on the B/C tasks - built-in loop, then Aider architect, then the Roo Code
rem task folders (Roo Code itself runs in VS Code; 07_ROO_GRADE.bat adds it to the same report). 1-3 hours.
cd /d "%~dp0"
echo  Other apps (Chrome, Edge etc.) will be closed in 15 seconds to free RAM. Ctrl+C to cancel.
timeout /t 15
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\08_relay_compare.ps1" %*
pause
