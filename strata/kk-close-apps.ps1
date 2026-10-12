# Strata launcher helper (kk): free RAM/VRAM before starting Strata.
# GUI apps get a normal close request (unsaved work prompts are respected); servers are stopped.
$ErrorActionPreference = 'SilentlyContinue'

# 1) Apps closed politely (same as clicking X). Edit this list freely.
$gui = @('chrome','msedge','unsloth-studio','LM Studio','bambu-studio','steam','steamwebhelper',
         'Docker Desktop','blender','Unity','Unity Hub','UnrealEditor','EpicGamesLauncher',
         'Discord','LINE','Obsidian','Cursor','Antigravity','VRoidStudio','NVIDIA Overlay')
# 2) Background servers stopped outright (no unsaved data).
$srv = @('ollama','ollama app','strata','strata-vision')
# 3) Python processes stopped by command line (ComfyUI, Unsloth backend, an old Strata server).
$pyPatterns = @('*ComfyUI*','*unsloth*','*server.py*--engine strata*')

Write-Host ' Closing apps to free RAM/VRAM ...'
foreach ($n in $gui) { Get-Process -Name $n | ForEach-Object { Write-Host "  close: $($_.ProcessName)"; [void]$_.CloseMainWindow() } }
foreach ($n in $srv) { Get-Process -Name $n | ForEach-Object { Write-Host "  stop : $($_.ProcessName)"; Stop-Process -Id $_.Id -Force } }
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object {
    $cl = $_.CommandLine; $pyPatterns | Where-Object { $cl -like $_ } } | ForEach-Object {
    Write-Host "  stop : python ($($_.CommandLine.Substring(0,[Math]::Min(70,$_.CommandLine.Length))))"; Stop-Process -Id $_.ProcessId -Force }
# Whatever still holds Strata's port 8080 (an older server started another way)
Get-NetTCPConnection -LocalPort 8080 -State Listen | ForEach-Object {
    $p = Get-Process -Id $_.OwningProcess; Write-Host "  stop : port 8080 ($($p.ProcessName) pid $($p.Id))"; Stop-Process -Id $p.Id -Force }
Start-Sleep -Seconds 2
# Docker/WSL keep several GB in vmmem: shut WSL down too.
if (Get-Command wsl.exe) { if (Get-Process -Name 'vmmem','vmmemWSL') { Write-Host '  stop : WSL (vmmem)'; wsl.exe --shutdown } }

Start-Sleep -Seconds 8
$left = foreach ($n in $gui) { Get-Process -Name $n | Where-Object { $_.MainWindowHandle -ne 0 } }
if ($left) { Write-Host ' Still open (unsaved work?) - close them yourself:' ($left.ProcessName | Sort-Object -Unique) }
$free = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,1)
Write-Host " Free RAM now: $free GB"
