# 08_relay_compare.ps1 - one run, one report: SC117 (256K) on the B/C tasks three ways
#   1. the bench's own loop (one agent, the whole history in its context)
#   2. Aider architect mode (planner -> editor gets only the plan + files)        [skipped if aider is not installed]
#   3. Roo Code Orchestrator: the task folders are prepared here; you run them in VS Code, then 07_ROO_GRADE.bat
#      adds Roo Code to the same report.
param([int]$Ctx = 262144, [string]$Model = "sc117", [int]$LimitSec = 7200, [string]$Tasks = "B,C")
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Base = $PSScriptRoot
$Root = Join-Path $Base ("logs\night\relay-" + (Get-Date).ToString("yyyyMMdd-HHmm"))
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$Py = "$env:USERPROFILE\ai-models\Strata\.venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"
Write-Host "===== RELAY COMPARE: $Model, context $Ctx -> $Root ====="

Write-Host "--- 1/3 built-in loop ---"
& powershell -NoProfile -ExecutionPolicy Bypass -File "$Base\05_night_bench.ps1" -Only $Model -Ctx $Ctx -Tasks $Tasks -LimitSec $LimitSec -Root $Root

Write-Host "--- 2/3 Aider architect ---"
if (Get-Command aider -EA SilentlyContinue) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$Base\05_night_bench.ps1" -Agent aider -Only $Model -Ctx $Ctx -Tasks $Tasks -LimitSec $LimitSec -Root $Root
} else { Write-Host " skipped: aider is not installed (py -3.12 -m pip install aider-install, then aider-install)" }

Write-Host "--- 3/3 Roo Code task folders ---"
$tasksDir = "$env:USERPROFILE\roo-bench\tasks"
& $Py "$Base\night_bench.py" prepare --out $tasksDir --tasks $Tasks
[System.IO.File]::WriteAllText((Join-Path $Base "logs\night\RELAY_LATEST.txt"), $Root, [System.Text.UTF8Encoding]::new($false))
& $Py "$Base\night_bench.py" report --root $Root | Out-Null
Write-Host ""
Write-Host "===== done: $Root\REPORT.md (built-in loop + Aider) ====="
Write-Host " Roo Code: start Strata SC117 (desktop shortcut), open each folder of $tasksDir in VS Code,"
Write-Host " Orchestrator mode, send: TASK.md の指示を実行してください。  Then 07_ROO_GRADE.bat adds it to this report."
