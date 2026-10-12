# make_shortcut.ps1 (kk): put a desktop shortcut that starts Strata-Orca.bat (or -Launcher Strata-SC117.bat).
param([string]$Folder = "$env:USERPROFILE\work", [string]$Name = "Strata Orca (files)", [string]$Launcher = "Strata-Orca.bat")
$ErrorActionPreference = "Stop"
$bat = Join-Path $PSScriptRoot $Launcher
if (-not (Test-Path $bat)) { throw "missing: $bat" }
if (-not (Test-Path $Folder)) { New-Item -ItemType Directory -Force -Path $Folder | Out-Null }
$desktop = [Environment]::GetFolderPath("Desktop")   # also right when the desktop is in OneDrive
$lnk = Join-Path $desktop "$Name.lnk"
$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($lnk)
# Target the .bat itself (not cmd.exe): Explorer then accepts a folder dropped on the shortcut and passes it after
# $Folder, and Strata-Orca.bat uses the dropped one.
$s.TargetPath = $bat
$s.Arguments = "`"$Folder`""
$s.WorkingDirectory = Split-Path $PSScriptRoot -Parent
$s.IconLocation = "$env:SystemRoot\System32\imageres.dll,109"
$s.Description = "$Name + files in $Folder"
$s.Save()
Write-Host " Shortcut created: $lnk"
Write-Host " Double-click: $Name with the files in $Folder"
Write-Host " Drop a folder on it: the same, with that folder instead"
