@echo off
rem Compaction test (kk): SC117 at 256K does a 6-turn file job, compacted the way the chat page does it, and once
rem without; both graded, REPORT.md written and pushed to GitHub (results\compact-<time>\). About 20-60 minutes.
rem   09_COMPACT_TEST.bat -NoPush     keep the results local
cd /d "%~dp0"
echo  Other apps (Chrome, Edge etc.) will be closed in 15 seconds to free RAM. Ctrl+C to cancel.
timeout /t 15
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\09_compact_test.ps1" %*
pause
