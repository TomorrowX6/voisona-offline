# Offline VoiSona launcher: start the local mock server, then VoiSona.
# Run this instead of the normal shortcut while offline.
$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mock = Join-Path $dir 'mock_server.py'
$exe  = Join-Path $dir 'VoiSona.exe'

# 1. start mock server if not already listening on 18080
$already = $false
try {
  $c = [Net.Sockets.TcpClient]::new()
  $c.Connect('127.0.0.1', 18080)
  $c.Close()
  $already = $true
} catch {}

if (-not $already) {
  Start-Process -FilePath 'python' -ArgumentList @("`"$mock`"") -WindowStyle Minimized
  Start-Sleep -Seconds 2
  Write-Host "[offline] mock server started on http://127.0.0.1:18080/"
} else {
  Write-Host "[offline] mock server already running"
}

# 2. launch VoiSona
Start-Process -FilePath $exe -WorkingDirectory $dir
Write-Host "[offline] VoiSona launched"
