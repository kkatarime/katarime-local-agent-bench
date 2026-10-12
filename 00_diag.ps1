# 00_diag.ps1 - what is available for the local agent test (read-only, no downloads)
$ErrorActionPreference = "Continue"
$log = Join-Path $PSScriptRoot "logs\00_diag.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
Start-Transcript -Path $log -Force | Out-Null

Write-Output "===== 1. GPU ====="
& nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used --format=csv 2>&1

Write-Output "===== 2. llama-server ====="
Get-ChildItem "$env:USERPROFILE\ai-models\llama.cpp" -Recurse -Filter llama-server.exe -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }

Write-Output "===== 3. GGUF (abliterated / uncensored first) ====="
foreach ($d in @("$env:USERPROFILE\ai-models", "$env:USERPROFILE\.cache\huggingface\hub", "$env:USERPROFILE\.lmstudio\models", "$env:USERPROFILE\.unsloth", "$env:USERPROFILE\.cache\unsloth")) {
  if (Test-Path $d) {
    Get-ChildItem $d -Recurse -Filter *.gguf -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -notmatch 'mmproj' } |
      Select-Object @{n='GB';e={[math]::Round($_.Length/1GB,1)}}, @{n='abl';e={[bool]($_.Name -match 'ablit|uncensor')}}, FullName |
      Sort-Object abl, GB -Descending | Format-Table -AutoSize | Out-String -Width 400
  }
}

Write-Output "===== 4. Python ====="
foreach ($c in @("python","py","python3")) {
  $p = Get-Command $c -ErrorAction SilentlyContinue
  if ($p) { "{0} -> {1}" -f $c, $p.Source; & $p.Source -c "import sys;print(sys.version)" 2>&1 } else { "MISS: $c" }
}

Write-Output "===== 5. Unsloth / OpenCode ====="
foreach ($c in @("unsloth","unsloth-studio","opencode")) {
  $p = Get-Command $c -ErrorAction SilentlyContinue
  if ($p) { "OK  : $c -> $($p.Source)" } else { "MISS: $c" }
}
$u = Get-Command unsloth -ErrorAction SilentlyContinue
if ($u) { Write-Output "--- unsloth --help (look for disable-tools) ---"; & $u.Source --help 2>&1 | Select-Object -First 60 }

Write-Output "===== 6. Port 8085 ====="
$c = Get-NetTCPConnection -LocalPort 8085 -State Listen -ErrorAction SilentlyContinue
if ($c) { "IN USE by PID $($c.OwningProcess)" } else { "free" }

Write-Output "===== DONE ====="
Stop-Transcript | Out-Null
