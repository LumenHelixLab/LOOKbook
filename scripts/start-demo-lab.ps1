# Start lookBOOK Demo Lab (API + UI on port 8042). Safe to run from any directory.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$port = if ($env:LOOKBOOK_LAB_PORT) { $env:LOOKBOOK_LAB_PORT } else { "8042" }

# Free the port if a stale lab_server is still listening
Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }

$url = "http://127.0.0.1:$port/"
Write-Host ""
Write-Host "lookBOOK Demo Lab" -ForegroundColor Cyan
Write-Host "  Open: $url" -ForegroundColor Green
Write-Host "  (API + UI — do not use port 8766)" -ForegroundColor DarkGray
Write-Host ""

Start-Process $url
python -m lookbook.lab_server