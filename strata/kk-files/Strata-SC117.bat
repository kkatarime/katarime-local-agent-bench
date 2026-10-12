@echo off
rem One click (kk): SC117 uncensored GSQ-RCO + kk-files (run kk-sc117\SETUP-SC117.bat once first).
rem   Strata-SC117.bat              %USERPROFILE%\work
rem   Strata-SC117.bat "D:\folder"  that folder (also: drop a folder on this file or its shortcut)
rem   set SC117=IQ2_XS before it to use another prepared size (default IQ3_XXS)
setlocal
set "WORK=%~1"
if not "%~2"=="" set "WORK=%~2"
if "%WORK%"=="" set "WORK=%USERPROFILE%\work"
if not exist "%WORK%\" (
  if exist "%WORK%" ( echo  Drop a folder, not a file: "%WORK%" & pause & exit /b 1 )
  mkdir "%WORK%"
)
if "%SC117%"=="" set "SC117=iq3_xxs"
if not exist "%~dp0..\kk-sc117\sc117-%SC117%.json" ( echo  Not prepared yet: sc117-%SC117%.json - run kk-sc117\SETUP-SC117.bat ^(Swift: SETUP-SC117-SWIFT.bat^) first. & pause & exit /b 1 )
call "%~dp0Strata-Files.bat" "%WORK%" --config "kk-sc117\sc117-%SC117%.json"
endlocal
