# 02_game_bench.ps1 - run T1..T6 (T6 = Breakout game) on several local models, 1 hour cap each, back to back
param([int]$LimitSec = 3600, [int]$Port = 8085, [string]$Only = "")
$ErrorActionPreference = "Continue"
$Base = $PSScriptRoot
$Root = Join-Path $Base "logs\bench"
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$U8 = [System.Text.UTF8Encoding]::new($false)
$RunLog = Join-Path $Root "bench.log"; $Status = Join-Path $Root "STATUS.txt"; $Sum = Join-Path $Root "SUMMARY.csv"
function Say($m) { $l = (Get-Date).ToString("MM-dd HH:mm:ss") + "  " + $m; Write-Host $l; [System.IO.File]::AppendAllText($RunLog, $l + "`r`n", $U8) }
function SetStatus($m) { [System.IO.File]::WriteAllText($Status, (Get-Date).ToString("yyyy-MM-dd HH:mm:ss") + "  " + $m, $U8) }
function IsLocal($a) { return ($a -match '^(127\.|0\.0\.0\.0$|::1$|::$)') }

# keep the PC awake for the whole run (ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
Add-Type -Namespace W -Name P -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[void][W.P]::SetThreadExecutionState([uint32]2147483649)

$M = "$env:USERPROFILE\ai-models\bench-models"
$StrataDir = "$env:USERPROFILE\ai-models\Strata"
$StrataPy = "$StrataDir\.venv\Scripts\python.exe"
$HF = "$env:USERPROFILE\.cache\huggingface\hub"
function FindGguf($dir, $name) { (Get-ChildItem $dir -Recurse -Filter $name -ErrorAction SilentlyContinue | Select-Object -First 1).FullName }
$configs = @(
  @{ name="qwen36-35b-a3b_think-on";  model="$M\Huihui-Qwen3.6-35B-A3B-abliterated.IQ4_XS.gguf"; extra=@("--n-cpu-moe","12"); think="on" },
  @{ name="qwen36-35b-a3b_think-off"; model="$M\Huihui-Qwen3.6-35B-A3B-abliterated.IQ4_XS.gguf"; extra=@("--n-cpu-moe","12"); think="off" },
  @{ name="glm47-flash";              model="$M\Huihui-GLM-4.7-Flash-abliterated.i1-IQ4_XS.gguf"; extra=@("--n-cpu-moe","12"); think="on" },
  @{ name="qwen38-27b-abl-dense";     model=(FindGguf $HF "qwen3.8-27b-abliterated-3.69bpw-12GB-MTP.gguf"); extra=@("-fa","on","-ctk","q8_0","-ctv","q8_0"); think="on" },
  # Strata (Qwen3.8-Flash-Next 125B MoE IQ3_XXS, RAM offload). "max" thinking never finished code gen -> medium
  @{ name="strata-qwen38-flash-next_medium"; engine="strata"; model="$StrataDir\strata-iq3_xxs.json";       think="on"; effort="medium" },
  @{ name="strata-orca-uncensored_medium";   engine="strata"; model="$StrataDir\kk-orca\orca-iq3_xxs.json"; think="on"; effort="medium" }
)
if ($Only) { $want = $Only -split ","; $configs = @($configs | Where-Object { $want -contains $_.name }) }
$Server = (Get-ChildItem "$env:USERPROFILE\ai-models\llama.cpp" -Recurse -Filter llama-server.exe -ErrorAction SilentlyContinue |
           Sort-Object { $_.FullName -notmatch 'cuda' } | Select-Object -First 1).FullName
$Py = $null
$cands = @(Get-ChildItem "$env:LOCALAPPDATA\Python" -Recurse -Filter python.exe -Depth 1 -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object { $_.FullName })
foreach ($c in @("py","python")) { $g = Get-Command $c -ErrorAction SilentlyContinue; if ($g) { $cands += $g.Source } }
foreach ($c in $cands) { $v = & $c -c "import sys;print(sys.version_info[0]*100+sys.version_info[1])" 2>$null; if ($LASTEXITCODE -eq 0 -and [int]("0"+$v) -ge 307) { $Py = $c; break } }
Say "===== GAME BENCH start (limit $LimitSec s per model) ====="
Say "server=$Server python=$Py"
if (-not $Server -or -not $Py) { Say "ERROR: server or python missing"; SetStatus "FAILED"; exit 1 }
if (-not (Test-Path $Sum)) { [System.IO.File]::WriteAllText($Sum, "model,task,result,steps,completion_tokens,seconds,error`r`n", $U8) }

function StopStrata {
  Get-Process strata,strata-vision -EA SilentlyContinue | Stop-Process -Force
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*server.py*--engine strata*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  Get-NetTCPConnection -LocalPort $Port -State Listen -EA SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
}
function StartStrata($cfg, $dir) {
  StopStrata; Start-Sleep 3
  $a = @("`"$StrataDir\serve\server.py`"", "--engine", "strata", "--config", "`"$($cfg.model)`"", "--host", "127.0.0.1", "--port", "$Port")
  $p = Start-Process -FilePath $StrataPy -ArgumentList $a -WorkingDirectory $StrataDir -PassThru -WindowStyle Hidden `
         -RedirectStandardOutput (Join-Path $dir "server.out.log") -RedirectStandardError (Join-Path $dir "server.err.log")
  for ($i = 0; $i -lt 450; $i++) {   # 125B load from disk: up to 15 min
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

function StartServer($cfg, $ctx, $dir) {
  $a = @("-m", "`"$($cfg.model)`"", "-ngl", "99", "-c", "$ctx", "--host", "127.0.0.1", "--port", "$Port", "--jinja") + $cfg.extra
  $p = Start-Process -FilePath $Server -ArgumentList $a -PassThru -WindowStyle Hidden `
         -RedirectStandardOutput (Join-Path $dir "server.out.log") -RedirectStandardError (Join-Path $dir "server.err.log")
  for ($i = 0; $i -lt 150; $i++) {
    Start-Sleep 2
    if ($p.HasExited) { return $null }
    try {
      $rq = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:$Port/health")
      $rq.Proxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy(); $rq.Timeout = 2000
      $rs = $rq.GetResponse(); $ok = ([int]$rs.StatusCode -eq 200); $rs.Close()
      if ($ok) { return $p }
    } catch { }
  }
  if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
  return $null
}

$n = 0
foreach ($cfg in $configs) {
  $n++
  $dir = Join-Path $Root $cfg.name
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  SetStatus "$n/$($configs.Count) $($cfg.name)"
  Say "----- [$n/$($configs.Count)] $($cfg.name) -----"
  if (-not $cfg.model -or -not (Test-Path $cfg.model)) { Say "SKIP: model not found"; continue }
  $t0 = Get-Date
  $srv = $null
  if ($cfg.engine -eq "strata") {
    Say "freeing RAM/VRAM (kk-close-apps.ps1)"
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$StrataDir\kk-close-apps.ps1" | ForEach-Object { Say "  $_" }
    $srv = StartStrata $cfg $dir
    if ($srv) { Say "strata up PID $($srv.Id) after $([int]((Get-Date)-$t0).TotalSeconds) s" }
    else { Say "strata failed. stderr tail:"; Get-Content (Join-Path $dir "server.err.log") -Tail 8 -EA SilentlyContinue | ForEach-Object { Say "  $_" } }
  }
  else { foreach ($ctx in @(32768, 16384)) {
    $srv = StartServer $cfg $ctx $dir
    if ($srv) { Say "server up ctx=$ctx PID $($srv.Id) after $([int]((Get-Date)-$t0).TotalSeconds) s"; break }
    Say "server failed at ctx=$ctx. stderr tail:"
    Get-Content (Join-Path $dir "server.err.log") -Tail 8 -ErrorAction SilentlyContinue | ForEach-Object { Say "  $_" }
  } }
  if (-not $srv) { Say "SKIP: server could not start"; continue }
  $remain = [int]($LimitSec - ((Get-Date) - $t0).TotalSeconds)
  $env:PYTHONIOENCODING = "utf-8"
  $agArgs = @("`"$Base\agent.py`"", "--url", "http://127.0.0.1:$Port", "--think", $cfg.think, "--max-tokens", "16384",
              "--deadline", "$remain", "--logdir", "`"$dir`"")
  if ($cfg.effort) { $agArgs += @("--effort", $cfg.effort) }
  $ag = Start-Process -FilePath $Py -PassThru -NoNewWindow -ArgumentList $agArgs `
          -RedirectStandardOutput (Join-Path $dir "agent.out.log") -RedirectStandardError (Join-Path $dir "agent.err.log")
  $ext = @{}
  while (-not $ag.HasExited) {
    $pids = @($srv.Id, $ag.Id) + @(Get-Process strata,strata-vision -EA SilentlyContinue | ForEach-Object { $_.Id })
    foreach ($pid_ in $pids) {
      Get-NetTCPConnection -OwningProcess $pid_ -ErrorAction SilentlyContinue | Where-Object { $_.State -ne 'Listen' -and -not (IsLocal $_.RemoteAddress) } |
        ForEach-Object { $ext["$($_.RemoteAddress):$($_.RemotePort)"] = $true }
    }
    if (((Get-Date) - $t0).TotalSeconds -gt ($LimitSec + 90)) { Say "HARD LIMIT: killing agent"; Stop-Process -Id $ag.Id -Force; break }
    Start-Sleep 3
  }
  if (-not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
  if ($cfg.engine -eq "strata") { StopStrata; Start-Sleep 15 }
  Start-Sleep 5
  Get-Content (Join-Path $dir "agent.out.log") -ErrorAction SilentlyContinue | ForEach-Object { Say "  $_" }
  if ($ext.Count) { Say "EXTERNAL TCP: $($ext.Keys -join ', ')" } else { Say "EXTERNAL TCP: none" }
  $res = Join-Path $dir "results.csv"
  if (Test-Path $res) {
    Import-Csv $res | ForEach-Object {
      [System.IO.File]::AppendAllText($Sum, ("{0},{1},{2},{3},{4},{5},{6}`r`n" -f $cfg.name, $_.task, $_.result, $_.steps, $_.completion_tokens, $_.seconds, $_.error), $U8)
    }
  }
  Say ("elapsed {0:n0} s, game.html: {1}" -f ((Get-Date) - $t0).TotalSeconds, (Test-Path (Join-Path $dir "game.html")))
}
[void][W.P]::SetThreadExecutionState([uint32]2147483648)
Say "===== GAME BENCH done ====="
SetStatus "DONE"
