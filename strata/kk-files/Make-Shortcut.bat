@echo off
rem Create the desktop shortcut "Strata Orca (files)" (kk). Run once.
rem   Make-Shortcut.bat              the shortcut uses %USERPROFILE%\work
rem   Make-Shortcut.bat "D:\folder"  the shortcut uses that folder
setlocal
if "%~1"=="" ( powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_shortcut.ps1" ) else ( powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_shortcut.ps1" -Folder "%~1" )
pause
endlocal
