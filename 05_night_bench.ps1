# 05_night_bench.ps1 - overnight: every Strata model, one after another, through night_bench.py (long context,
# multi-file work, things to build), then logs\night\<time>\REPORT.md comparing them.
#   -Only "orca,sc117-swift"   just these     -LimitSec 7200   per model     -Ctx 65536 (0 = the config's own)
#   -Agent aider               the B/C tasks through aider --architect instead of the built-in loop
param([int]$LimitSec = 7200, [int]$Port = 8085, [string]$Only = "", [int]$Ctx = 65536, [string]$Tasks = "",
      [string]$Agent = "native", [string]$AiderCmd = "aider")
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8   # read the Python output (Japanese) as UTF-8, not the OEM code page
$Base = $PSScriptRoot
$Stamp = (Get-Date).ToString("yyyyMMdd-HHmm")
$Root = Join-Path $Base "logs\night\$Stamp"
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$U8 = [System.Text.UTF8Encoding]::new($false)
$RunLog = Join-Path $Root "night.log"; $Status = Join-Path $Base "logs\night\STATUS.txt"
function Say($m) { $l = (Get-Date).ToString("MM-dd HH:mm:ss") + "  " + $m; Write-Host $l; [System.IO.File]::AppendAllText($RunLog, $l + "`r`n", $U8) }
function SetStatus($m) { [System.IO.File]::WriteAllText($Status, (Get-Date).ToString("yyyy-MM-dd HH:mm:ss") + "  " + $m + "`r`n" + $Root, $U8) }

# keep the PC awake (ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
Add-Type -Namespace W -Name P -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[void][W.P]::SetThreadExecutionState([uint32]2147483649)

$StrataDir = "$env:USERPROFILE\ai-models\Strata"
$Py = "$StrataDir\.venv\Scripts\python.exe"
$models = @(
  @{ name="sc117-swift";     cfg="$StrataDir\kk-sc117\sc117-swift-iq3_xxs.json" },
  @{ name="orca";            cfg="$StrataDir\kk-orca\orca-iq3_xxs.json" },
  @{ name="sc117";           cfg="$StrataDir\kk-sc117\sc117-iq3_xxs.json" },
  @{ name="strata-standard"; cfg="$StrataDir\strata-iq3_xxs.json" }
)
if ($Only) { $want = $Only -split ","; $models = @($models | Where-Object { $want -contains $_.name }) }
$models = @($models | Where-Object { if (Test-Path $_.cfg) { $true } else { Say "skip $($_.name): no $($_.cfg)"; $false } })
Say "===== NIGHT BENCH start: $($models.Count) models, $LimitSec s each, context $Ctx -> $Root ====="
if (-not (Test-Path $Py)) { Say "ERROR: no $Py (install Strata first)"; SetStatus "FAILED"; exit 1 }
if (-not $models.Count) { Say "ERROR: no model config found"; SetStatus "FAILED"; exit 1 }

$env:PYTHONIOENCODING = "utf-8"
Say "self-test of the graders (no model) ..."
& $Py "$Base\night_bench.py" selftest 2>&1 | ForEach-Object { Say "  $_" }

function StopStrata {
  Get-Process strata,strata-vision -EA SilentlyContinue | Stop-Process -Force
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*server.py*--engine strata*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  Get-NetTCPConnection -LocalPort $Port -State Listen -EA SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
}
function StartStrata($cfgPath, $dir) {
  StopStrata; Start-Sleep 5
  $a = @("`"$StrataDir\serve\server.py`"", "--engine", "strata", "--config", "`"$cfgPath`"", "--host", "127.0.0.1", "--port", "$Port")
  $p = Start-Process -FilePath $Py -ArgumentList $a -WorkingDirectory $StrataDir -PassThru -WindowStyle Hidden `
         -RedirectStandardOutput (Join-Path $dir "server.out.log") -RedirectStandardError (Join-Path $dir "server.err.log")
  for ($i = 0; $i -lt 450; $i++) {   # loading 125B from disk: up to 15 min
    Start-Sleep 2
    if ($p.HasExited) { return $null }
    try {
      $rq = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:$Port/health")
      $rq.Proxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy(); $rq.Timeout = 2000
      $rs = $rq.GetResponse(); $txt = (New-Object System.IO.StreamReader($rs.GetResponseStream())).ReadToEnd(); $rs.Close()
      if ($txt -match '"loaded"\s*:\s*true') { return $p }
    } catch { }
  }
  StopStrata
  return $null
}
function CfgCtx($path) { $j = Get-Content $path -Raw | ConvertFrom-Json; $i = [array]::IndexOf($j.args, "--max-context"); if ($i -ge 0) { [int]$j.args[$i + 1] } else { 32768 } }

Say "freeing RAM/VRAM (kk-close-apps.ps1)"
& powershell -NoProfile -ExecutionPolicy Bypass -File "$StrataDir\kk-close-apps.ps1" | ForEach-Object { Say "  $_" }

$n = 0
foreach ($m in $models) {
  $n++
  $dir = Join-Path $Root $m.name
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  SetStatus "$n/$($models.Count) $($m.name)"
  Say "----- [$n/$($models.Count)] $($m.name) -----"
  $t0 = Get-Date
  $srv = $null; $useCtx = CfgCtx $m.cfg
  if ($Ctx -gt 0 -and $Ctx -ne $useCtx) {
    $big = Join-Path $dir "config-$Ctx.json"
    & $Py "$Base\night_bench.py" make-config --src $m.cfg --ctx $Ctx --out $big | ForEach-Object { Say "  $_" }
    $srv = StartStrata $big $dir
    if ($srv) { $useCtx = $Ctx } else {
      Say "context $Ctx did not start. stderr tail:"; Get-Content (Join-Path $dir "server.err.log") -Tail 6 -EA SilentlyContinue | ForEach-Object { Say "  $_" }
      Say "retrying with the config's own context ($useCtx)" }
  }
  if (-not $srv) { $srv = StartStrata $m.cfg $dir }
  if (-not $srv) { Say "SKIP: Strata could not start. stderr tail:"; Get-Content (Join-Path $dir "server.err.log") -Tail 8 -EA SilentlyContinue | ForEach-Object { Say "  $_" }; continue }
  Say "strata up (context $useCtx) after $([int]((Get-Date)-$t0).TotalSeconds) s"
  Get-Content (Join-Path $dir "server.out.log"), (Join-Path $dir "server.err.log") -EA SilentlyContinue |
    Select-String -Pattern "experts loaded|VRAM free|expert cache|ready:" | ForEach-Object { $_.Line } | Set-Content (Join-Path $dir "server-info.txt") -Encoding UTF8
  $remain = [int]($LimitSec - ((Get-Date) - $t0).TotalSeconds)
  if ($Agent -eq "aider") {
    $args2 = @("`"$Base\night_bench.py`"", "aider", "--url", "http://127.0.0.1:$Port", "--name", "$($m.name)-aider", "--ctx", "$useCtx",
               "--aider-cmd", "`"$AiderCmd`"", "--deadline", "$remain", "--logdir", "`"$dir`"")
  } else {
    $args2 = @("`"$Base\night_bench.py`"", "run", "--url", "http://127.0.0.1:$Port", "--name", $m.name, "--ctx", "$useCtx",
               "--deadline", "$remain", "--logdir", "`"$dir`"")
  }
  if ($Tasks) { $args2 += @("--tasks", $Tasks) }
  $ag = Start-Process -FilePath $Py -PassThru -NoNewWindow -ArgumentList $args2 -WorkingDirectory $Base `
          -RedirectStandardOutput (Join-Path $dir "bench.out.log") -RedirectStandardError (Join-Path $dir "bench.err.log")
  while (-not $ag.HasExited) {
    if (((Get-Date) - $t0).TotalSeconds -gt ($LimitSec + 300)) { Say "HARD LIMIT: stopping the bench"; Stop-Process -Id $ag.Id -Force; break }
    if ($srv.HasExited) { Say "Strata stopped during the run (see server.err.log)"; Start-Sleep 30; Stop-Process -Id $ag.Id -Force -EA SilentlyContinue; break }
    Start-Sleep 5
  }
  StopStrata; Start-Sleep 15
  Get-Content (Join-Path $dir "bench.out.log") -Encoding UTF8 -EA SilentlyContinue | Where-Object { $_ -match '\] .*/' } | ForEach-Object { Say "  $_" }
  & $Py "$Base\night_bench.py" report --root $Root | Out-Null
  Say ("elapsed {0:n0} s" -f ((Get-Date) - $t0).TotalSeconds)
}
& $Py "$Base\night_bench.py" report --root $Root | ForEach-Object { Say "  $_" }
[void][W.P]::SetThreadExecutionState([uint32]2147483648)
Say "===== NIGHT BENCH done: $Root\REPORT.md ====="
SetStatus "DONE"
