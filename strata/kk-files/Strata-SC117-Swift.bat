@echo off
rem One click (kk): SC117 uncensored Swift 1.5 + kk-files (run kk-sc117\SETUP-SC117-SWIFT.bat once first).
rem   Strata-SC117-Swift.bat              %USERPROFILE%\work
rem   Strata-SC117-Swift.bat "D:\folder"  that folder (also: drop a folder on this file or its shortcut)
rem   set SWIFT=IQ2_XS before it to use another prepared size (default IQ3_XXS)
setlocal
if "%SWIFT%"=="" set "SWIFT=iq3_xxs"
set "SC117=swift-%SWIFT%"
call "%~dp0Strata-SC117.bat" %*
endlocal
