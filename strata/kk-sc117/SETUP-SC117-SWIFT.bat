@echo off
rem SC117 uncensored Swift 1.5 (kk): download, then make the pack and kk-sc117\sc117-swift-<size>.json.
rem   SETUP-SC117-SWIFT.bat                 IQ3_XXS, 32K context
rem   SETUP-SC117-SWIFT.bat IQ2_XS 65536    another size (IQ2_XS or IQ3_XXS) / context
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" ( echo  Run Strata-Launch.bat once first ^(it installs Strata^). & pause & exit /b 1 )
set "Q=%~1"
if "%Q%"=="" set "Q=IQ3_XXS"
set "CTX=%~2"
if "%CTX%"=="" set "CTX=32768"
".venv\Scripts\python.exe" kk-sc117\download_sc117.py --model swift --quant %Q%
if errorlevel 1 ( pause & exit /b 1 )
".venv\Scripts\python.exe" kk-sc117\prepare_sc117.py --model swift --quant %Q% --context %CTX%
pause
endlocal
