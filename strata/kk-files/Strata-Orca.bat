@echo off
rem One click (kk): Strata Orca uncensored + kk-files. The model can read and edit the files in the work folder.
rem   Strata-Orca.bat              uses %USERPROFILE%\work (created if missing)
rem   Strata-Orca.bat "D:\folder"  uses that folder (also: drop a folder on this file or on its shortcut)
rem The desktop shortcut passes its own folder first, so a folder dropped on it arrives second and wins.
rem Closing the Strata window stops the model.
setlocal
set "WORK=%~1"
if not "%~2"=="" set "WORK=%~2"
if "%WORK%"=="" set "WORK=%USERPROFILE%\work"
if not exist "%WORK%\" (
  if exist "%WORK%" ( echo  Drop a folder, not a file: "%WORK%" & pause & exit /b 1 )
  mkdir "%WORK%"
)
call "%~dp0Strata-Files.bat" "%WORK%" --orca
endlocal
