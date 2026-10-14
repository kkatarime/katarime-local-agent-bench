# push_results.ps1 - copy a night-bench run's results into results\<run>\ and push them to GitHub, so they can be
# read from the repository. Transcripts and work folders stay local (large); reports, scores, small logs and the
# things the models built (artifacts) are copied.
#   push_results.ps1                  the newest run under logs\night
#   push_results.ps1 -Dir <folder>    that run
param([string]$Dir = "", [string]$Message = "")
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Base = $PSScriptRoot
if (-not $Dir) {
  $Dir = (Get-ChildItem (Join-Path $Base "logs\night") -Directory -EA SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1).FullName
}
if (-not $Dir -or -not (Test-Path $Dir)) { Write-Host " no results folder found under logs\night"; exit 1 }
$name = Split-Path $Dir -Leaf
$dst = Join-Path $Base "results\$name"
New-Item -ItemType Directory -Force $dst | Out-Null
foreach ($f in @("REPORT.md", "summary.csv", "night.log")) { if (Test-Path "$Dir\$f") { Copy-Item "$Dir\$f" $dst -Force } }
Get-ChildItem $Dir -Directory | ForEach-Object {
  $sub = Join-Path $dst $_.Name
  New-Item -ItemType Directory -Force $sub | Out-Null
  Get-ChildItem $_.FullName -File | Where-Object { $_.Name -match '^(results\.json|server-info\.txt|compact-.*\.json|transcript\.jsonl|aider-.*\.log|bench\.(out|err)\.log|config-\d+\.json)$' } |
    ForEach-Object { Copy-Item $_.FullName $sub -Force }
  if (Test-Path "$($_.FullName)\artifacts") { Copy-Item "$($_.FullName)\artifacts" $sub -Recurse -Force }
}
Write-Host " copied to $dst"
$branch = (git -C $Base rev-parse --abbrev-ref HEAD).Trim()
if (-not $Message) { $Message = "Bench results $name" }
git -C $Base add -- "results/$name"
git -C $Base commit -q -m $Message
if ($LASTEXITCODE -ne 0) { Write-Host " nothing new to commit"; exit 0 }
git -C $Base pull -q --rebase origin $branch
git -C $Base push -q origin $branch
if ($LASTEXITCODE -eq 0) { Write-Host " pushed: results/$name ($branch)" } else { Write-Host " push failed (see above); the commit is kept locally, run this again later" }
