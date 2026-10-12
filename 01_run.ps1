# 01_run.ps1 - start llama-server (local only), run 5 file tasks, watch outbound TCP
param(
  [string]$Model = "$env:USERPROFILE\ai-models\bench-models\Huihui-Qwen3.6-35B-A3B-abliterated.IQ4_XS.gguf",
  [int]$NCpuMoe = 12,
  [int]$Ctx = 16384,
  [int]$Port = 8085
)
$ErrorActionPreference = "Continue"
$Base = $PSScriptRoot
$Logs = Join-Path $Base "logs"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
$U8 = [System.Text.UTF8Encoding]::new($false)
$RunLog = Join-Path $Logs "run.log"; $Status = Join-Path $Logs "STATUS.txt"; $Net = Join-Path $Logs "net.csv"
[System.IO.File]::WriteAllText($RunLog, "", $U8)
function Say($m) { $l = (Get-Date).ToString("HH:mm:ss") + "  " + $m; Write-Host $l; [System.IO.File]::AppendAllText($RunLog, $l + "`r`n", $U8) }
function SetStatus($m) { [System.IO.File]::WriteAllText($Status, (Get-Date).ToString("yyyy-MM-dd HH:mm:ss") + "  " + $m, $U8) }
function IsLocal($a) { return ($a -match '^(127\.|0\.0\.0\.0$|::1$|::$)') }
$srv = $null
try {
  SetStatus "1/4 preflight"
  $Server = (Get-ChildItem "$env:USERPROFILE\ai-models\llama.cpp" -Recurse -Filter llama-server.exe -ErrorAction SilentlyContinue |
             Sort-Object { $_.FullName -notmatch 'cuda' } | Select-Object -First 1).FullName
  if (-not $Server) { throw "llama-server.exe not found under ai-models\llama.cpp" }
  if (-not (Test-Path $Model)) { throw "model not found: $Model" }
  $Py = $null
  $cands = @(Get-ChildItem "$env:LOCALAPPDATA\Python" -Recurse -Filter python.exe -Depth 1 -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object { $_.FullName })
  $cands += @(Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Recurse -Filter python.exe -Depth 1 -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
  foreach ($c in @("py","python","python3")) { $g = Get-Command $c -ErrorAction SilentlyContinue; if ($g) { $cands += $g.Source } }
  foreach ($c in $cands) {
    $v = & $c -c "import sys;print(sys.version_info[0]*100+sys.version_info[1])" 2>$null
    if ($LASTEXITCODE -eq 0 -and [int]("0"+$v) -ge 307) { $Py = $c; break }
  }
  if (-not $Py) { throw "no working python >= 3.7 found" }
  $used = [int]((& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>$null | Select-Object -First 1))
  Say "VRAM used before start: $used MiB"
  if ($used -gt 4000 -and -not $env:LA_IGNORE_VRAM) {
    throw "VRAM already $used MiB in use. Close Unsloth Studio / ComfyUI / LM Studio / games, then rerun (or set LA_IGNORE_VRAM=1)"
  }
  if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "port $Port already in use" }
  Say "server = $Server"; Say "model  = $Model"; Say "python = $Py"; Say "ncmoe=$NCpuMoe ctx=$Ctx port=$Port"

  SetStatus "2/4 loading model"
  $env:HF_HUB_OFFLINE = "1"
  $sargs = @("-m", "`"$Model`"", "-ngl", "99", "--n-cpu-moe", "$NCpuMoe", "-c", "$Ctx",
             "--host", "127.0.0.1", "--port", "$Port", "--jinja")
  $srv = Start-Process -FilePath $Server -ArgumentList $sargs -PassThru -WindowStyle Hidden `
           -RedirectStandardOutput (Join-Path $Logs "server.out.log") -RedirectStandardError (Join-Path $Logs "server.err.log")
  Say "llama-server PID $($srv.Id)"
  $ready = $false
  for ($i = 0; $i -lt 150; $i++) {
    Start-Sleep 2
    if ($srv.HasExited) { break }
    try {
      $rq = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:$Port/health")
      $rq.Proxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy(); $rq.Timeout = 2000
      $rs = $rq.GetResponse(); if ([int]$rs.StatusCode -eq 200) { $ready = $true }; $rs.Close()
      if ($ready) { break }
    } catch { }
  }
  if (-not $ready) {
    Say "server did not become ready. stderr tail:"
    Get-Content (Join-Path $Logs "server.err.log") -Tail 30 | ForEach-Object { Say "  $_" }
    throw "server not ready"
  }
  Say "server ready after $([int]($i*2)) s"

  SetStatus "3/4 running tasks"
  $env:PYTHONIOENCODING = "utf-8"
  [System.IO.File]::WriteAllText($Net, "time,pid,local,remote,state`r`n", $U8)
  $ext = @{}; $samples = 0
  foreach ($mode in @("on","off")) {
    SetStatus "3/4 running tasks (think=$mode)"
    $out = Join-Path $Logs "agent_think_$mode.out.log"
    $ag = Start-Process -FilePath $Py -ArgumentList @("`"$Base\agent.py`"", "--url", "http://127.0.0.1:$Port", "--think", $mode, "--tag", "_think_$mode") -PassThru -NoNewWindow `
            -RedirectStandardOutput $out -RedirectStandardError (Join-Path $Logs "agent_think_$mode.err.log")
    while (-not $ag.HasExited) {
      foreach ($pid_ in @($srv.Id, $ag.Id)) {
        Get-NetTCPConnection -OwningProcess $pid_ -ErrorAction SilentlyContinue | Where-Object { $_.State -ne 'Listen' } | ForEach-Object {
          $line = "{0},{1},{2}:{3},{4}:{5},{6}" -f (Get-Date).ToString("HH:mm:ss"), $pid_, $_.LocalAddress, $_.LocalPort, $_.RemoteAddress, $_.RemotePort, $_.State
          [System.IO.File]::AppendAllText($Net, $line + "`r`n", $U8)
          if (-not (IsLocal $_.RemoteAddress)) { $ext["$($_.RemoteAddress):$($_.RemotePort)"] = $true }
        }
      }
      $samples++; Start-Sleep 2
    }
    Say "think=$mode exit code $($ag.ExitCode)"
    Get-Content $out | ForEach-Object { Say "  $_" }
  }
  Say "net samples $samples"
  if ($ext.Count -eq 0) { Say "EXTERNAL TCP: none (only loopback seen)" }
  else { Say "EXTERNAL TCP: $($ext.Count) -> $($ext.Keys -join ', ')" }
  SetStatus "4/4 DONE"
}
catch { Say "ERROR: $_"; SetStatus "FAILED: $_" }
finally {
  if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force; Say "llama-server stopped" }
}
