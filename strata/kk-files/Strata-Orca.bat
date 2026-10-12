@echo off
rem One click (kk): Strata Orca uncensored + kk-files. The model can read and edit the files in the work folder.
rem   Strata-Orca.bat              uses %USERPROFILE%\work (created if missing)
rem   Strata-Orca.bat "D:\folder"  uses that folder
rem Closing the Strata window stops the model.
setlocal
set "WORK=%~1"
if "%WORK%"=="" set "WORK=%USERPROFILE%\work"
if not exist "%WORK%" mkdir "%WORK%"
call "%~dp0Strata-Files.bat" "%WORK%" --orca
endlocal
