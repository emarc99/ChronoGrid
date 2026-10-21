# Start ChronoGrid (MCP server + API + ambient screen) on http://127.0.0.1:8787
#   .\scripts\run.ps1            # build the web UI if needed and start
#   .\scripts\run.ps1 -Seed      # also reset the ledger with demo history
#   .\scripts\run.ps1 -Rebuild   # force a web rebuild
param([switch]$Seed, [switch]$Rebuild)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    python -m venv .venv
    & $python -m pip install -e ".[dev]"
}

$listener = Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue
if ($listener) { Stop-Process -Id $listener.OwningProcess -Force; Start-Sleep 1 }

if ($Rebuild -or -not (Test-Path "web\dist\index.html")) {
    Push-Location web
    if (-not (Test-Path node_modules)) { npm install }
    npm run build
    Pop-Location
}

if ($Seed) { & $python -m seed.seed }
& $python -m server.api
