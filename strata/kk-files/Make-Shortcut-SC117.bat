@echo off
rem Create the desktop shortcut "Strata SC117 (files)" (kk). Run once, after kk-sc117\SETUP-SC117.bat.
rem   Make-Shortcut-SC117.bat              the shortcut uses %USERPROFILE%\work
rem   Make-Shortcut-SC117.bat "D:\folder"  the shortcut uses that folder
setlocal
set "F=%~1"
if "%F%"=="" set "F=%USERPROFILE%\work"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_shortcut.ps1" -Folder "%F%" -Name "Strata SC117 (files)" -Launcher "Strata-SC117.bat"
pause
endlocal
