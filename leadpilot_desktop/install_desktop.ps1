# Create a Windows desktop shortcut for LeadPilot B2B companion.
# ASCII shortcut filename avoids Windows PowerShell 5.1 UTF-8-without-BOM issues.
$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$app = Join-Path $project "leadpilot_desktop.py"
if (-not (Test-Path -LiteralPath $app)) { throw "Missing leadpilot_desktop.py" }

$exe = (& py -3 -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1)
if (-not $exe -or -not (Test-Path -LiteralPath $exe)) {
    throw "Python 3 not found. Run: py --version"
}
$pythonw = Join-Path (Split-Path -Parent $exe) "pythonw.exe"
if (-not (Test-Path -LiteralPath $pythonw)) { $pythonw = $exe }

$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
if (-not $desktop -or -not (Test-Path -LiteralPath $desktop)) {
    $desktop = Join-Path $env:USERPROFILE "Desktop"
}
if (-not (Test-Path -LiteralPath $desktop)) {
    throw "Desktop directory unavailable. Create a shortcut manually from launch.bat."
}
# Desktop icons can be renamed by the user after creation.
$shortcutPath = [System.IO.Path]::GetFullPath((Join-Path $desktop "LeadPilot B2B Workspace.lnk"))
if (-not $shortcutPath.EndsWith(".lnk", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Invalid shortcut extension"
}
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = ('"' + $app + '"')
$shortcut.WorkingDirectory = $project
$shortcut.Description = "Horyalf LeadPilot B2B workspace"
$shortcut.Save()
Write-Host "Shortcut created:" $shortcutPath
Write-Host "Double-click it to open the LeadPilot B2B workspace."
