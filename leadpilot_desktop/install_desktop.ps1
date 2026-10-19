# Creates desktop shortcut pointing to Pythonw, without requesting admin access.
$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$app = Join-Path $project "leadpilot_desktop.py"
if (-not (Test-Path $app)) { throw "Missing leadpilot_desktop.py" }
try { $exe = (& py -3 -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1) }
catch { throw "Python 3 not found. Please install Python 3 with tkinter and retry." }
if (-not $exe -or -not (Test-Path $exe)) { throw "Python 3 not found" }
$pythonw = Join-Path (Split-Path -Parent $exe) "pythonw.exe"
if (-not (Test-Path $pythonw)) { $pythonw = $exe }
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "LeadPilot B2B 工作台.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = ('"' + $app + '"')
$shortcut.WorkingDirectory = $project
$shortcut.Description = "Horyalf LeadPilot B2B local workspace"
$shortcut.Save()
Write-Host "Shortcut created:" $shortcutPath
Write-Host "Open it to launch the local B2B workspace."
