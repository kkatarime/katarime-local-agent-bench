# make_shortcut.ps1 (kk): put a "Strata Orca (files)" shortcut on the desktop that starts Strata-Orca.bat.
param([string]$Folder = "$env:USERPROFILE\work", [string]$Name = "Strata Orca (files)")
$ErrorActionPreference = "Stop"
$bat = Join-Path $PSScriptRoot "Strata-Orca.bat"
if (-not (Test-Path $bat)) { throw "missing: $bat" }
if (-not (Test-Path $Folder)) { New-Item -ItemType Directory -Force -Path $Folder | Out-Null }
$desktop = [Environment]::GetFolderPath("Desktop")   # also right when the desktop is in OneDrive
$lnk = Join-Path $desktop "$Name.lnk"
$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($lnk)
$s.TargetPath = "$env:SystemRoot\System32\cmd.exe"
$s.Arguments = "/c `"`"$bat`" `"$Folder`"`""
$s.WorkingDirectory = Split-Path $PSScriptRoot -Parent
$s.IconLocation = "$env:SystemRoot\System32\imageres.dll,109"
$s.Description = "Strata Orca uncensored + files in $Folder"
$s.Save()
Write-Host " Shortcut created: $lnk"
Write-Host " It starts Strata Orca (uncensored) with the files in: $Folder"
