@echo off
rem Strata + kk-files (kk): the model can read and edit the files in ONE folder from its chat.
rem   Strata-Files.bat                       asks for the folder
rem   Strata-Files.bat "C:\Users\me\work"     that folder, the most recently used model
rem   Strata-Files.bat "C:\Users\me\work" --orca --read-only
rem Closing the Strata window stops the model.
setlocal
title Strata + files
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" ( echo  Run Strata-Launch.bat once first ^(it installs Strata^). & pause & exit /b 1 )
set "FOLDER=%~1"
if "%FOLDER%"=="" set /p "FOLDER=Folder the model may use (e.g. C:\Users\me\work): "
if "%FOLDER%"=="" exit /b 1
echo  Other apps will be closed in 5 seconds to free RAM (Ctrl+C to cancel) ...
timeout /t 5
powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\kk-close-apps.ps1"
".venv\Scripts\python.exe" kk-files\start_files.py --folder "%FOLDER%" %2 %3 %4 %5 %6
if errorlevel 1 pause
endlocal
