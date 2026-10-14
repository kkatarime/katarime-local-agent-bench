# 09_compact_test.ps1 - the compaction test on SC117 (256K) and the results pushed, in one go:
#   Strata starts, night_bench.py compact-test runs a 6-turn file job twice (compacted after turn 4 as the chat page
#   does, and once without compaction), grades both, writes REPORT.md, then push_results.ps1 sends it to GitHub.
param([string]$Model = "sc117", [int]$Ctx = 262144, [switch]$NoPush)
$Base = $PSScriptRoot
$Root = Join-Path $Base ("logs\night\compact-" + (Get-Date).ToString("yyyyMMdd-HHmm"))
& powershell -NoProfile -ExecutionPolicy Bypass -File "$Base\05_night_bench.ps1" -Agent compact -Only $Model -Ctx $Ctx -Root $Root -LimitSec 5400
if (-not $NoPush) { & powershell -NoProfile -ExecutionPolicy Bypass -File "$Base\push_results.ps1" -Dir $Root -Message "Compaction test results $(Split-Path $Root -Leaf)" }
Write-Host ""
Write-Host " Report: $Root\REPORT.md"
