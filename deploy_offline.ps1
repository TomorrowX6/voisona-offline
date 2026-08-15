# Deploy the offline-patched VoiSona.exe into Program Files.
# Run this script AS ADMINISTRATOR (right-click -> Run with PowerShell as admin),
# or from an elevated prompt. Unprivileged copies to Program Files are denied.
$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $dir 'VoiSona.exe'
$dst = 'C:\Program Files\Techno-Speech\VoiSona\VoiSona.exe'

if (-not (Test-Path $src)) { throw "patched exe not found: $src" }
if (-not (Test-Path $dst)) { throw "installed exe not found: $dst" }

# is this process elevated?
$id  = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr  = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw "Not elevated. Run PowerShell as administrator and re-run this script."
}

$bak = "$dst.bak_offline"
if (-not (Test-Path $bak)) { Copy-Item $dst $bak -Force; Write-Host "backed up -> $bak" }
Copy-Item $src $dst -Force
Write-Host "deployed -> $dst"
