@echo off
rem Create the desktop shortcut "Strata SC117 Swift (files)" (kk). Run once, after kk-sc117\SETUP-SC117-SWIFT.bat.
rem   Make-Shortcut-SC117-Swift.bat              the shortcut uses %USERPROFILE%\work
rem   Make-Shortcut-SC117-Swift.bat "D:\folder"  the shortcut uses that folder
setlocal
set "F=%~1"
if "%F%"=="" set "F=%USERPROFILE%\work"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_shortcut.ps1" -Folder "%F%" -Name "Strata SC117 Swift (files)" -Launcher "Strata-SC117-Swift.bat"
pause
endlocal
