# 07_roo.ps1 - Roo Code (Orchestrator mode) on the night-bench B/C tasks, by hand:
#   -Step prepare   task folders + TASK.md in %USERPROFILE%\roo-bench\tasks (refuses to overwrite; -Force to start over)
#   -Step grade     grade them; logs\night\roo-compare\REPORT.md next to SC117's own run (and the newest Aider run)
param([string]$Step = "prepare", [switch]$Force, [string]$Name = "sc117-roo-orchestrator")
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Base = $PSScriptRoot
$Py = "$env:USERPROFILE\ai-models\Strata\.venv\Scripts\python.exe"
$Tasks = "$env:USERPROFILE\roo-bench\tasks"
$env:PYTHONIOENCODING = "utf-8"
if ($Step -eq "prepare") {
  $a = @("$Base\night_bench.py", "prepare", "--out", $Tasks); if ($Force) { $a += "--force" }
  & $Py @a
  Write-Host ""
  Write-Host " Next: start Strata SC117, then in VS Code open each folder in $Tasks (File > Open Folder),"
  Write-Host " switch Roo Code to Orchestrator and send:  TASK.md の指示を実行してください。"
  Write-Host " When all 10 are done: 07_ROO_GRADE.bat"
  exit
}
$Root = Join-Path $Base "logs\night\roo-compare"
New-Item -ItemType Directory -Force -Path $Root | Out-Null
# the same model with the built-in loop (the 2026-10-13 night run), and the newest Aider run if there is one
$native = Join-Path $Base "results\night-20261013-0027\sc117\results.json"
if (Test-Path $native) { New-Item -ItemType Directory -Force "$Root\sc117" | Out-Null; Copy-Item $native "$Root\sc117\results.json" -Force }
$aider = Get-ChildItem (Join-Path $Base "logs\night") -Recurse -Filter results.json -EA SilentlyContinue |
  Where-Object { $_.FullName -notlike "*roo-compare*" -and (Get-Content $_.FullName -Raw -Encoding UTF8) -match '"name": "[^"]*-aider"' } |
  Sort-Object LastWriteTime | Select-Object -Last 1
if ($aider) { $d = "$Root\$($aider.Directory.Name)-aider"; New-Item -ItemType Directory -Force $d | Out-Null; Copy-Item $aider.FullName "$d\results.json" -Force }
& $Py "$Base\night_bench.py" grade --dir $Tasks --name $Name --root $Root --note "Roo Code Orchestrator"
Write-Host ""
Write-Host " Report: $Root\REPORT.md"
