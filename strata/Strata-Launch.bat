@echo off
rem Strata one-click launcher (kk): first run = install IQ3_XXS + start, later runs = start only.
rem Closing the Strata window stops the model.
setlocal
title Strata launcher
cd /d "%~dp0"

echo ============================================================
echo  Strata launcher
echo ============================================================
echo  All other apps will be closed in 5 seconds (Ctrl+C to cancel) ...
timeout /t 5
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kk-close-apps.ps1"
echo.

if exist "strata-*.json" (
  echo  Installed model found: starting Strata ...
  call "%~dp0START-HERE.bat" %*
) else (
  echo  First run: installing Qwen3.8-Flash-Next IQ3_XXS ^(about 76 GB download^) and starting ...
  call "%~dp0START-HERE.bat" --family qwen --model IQ3_XXS --vision no --yes %*
)
endlocal
