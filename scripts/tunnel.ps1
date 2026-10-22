# Expose ChronoGrid's MCP endpoint to the cloud (AgentCore Runtime) through a Cloudflare quick tunnel.
# Only /mcp with the bearer token is reachable through it (see tunnel_guard in server/api.py).
param([int]$Port = 8787)

$root = Split-Path $PSScriptRoot -Parent
$exe = Join-Path $root "tools\cloudflared.exe"
if (-not (Test-Path $exe)) {
    New-Item -ItemType Directory -Force (Split-Path $exe) | Out-Null
    Invoke-WebRequest -Uri https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe -OutFile $exe
}
$marker = Join-Path $root "data\public_url.txt"
Remove-Item $marker -ErrorAction SilentlyContinue

& $exe tunnel --no-autoupdate --url "http://127.0.0.1:$Port" 2>&1 | ForEach-Object {
    $line = "$_"
    Write-Host $line
    if ($line -match '(https://[a-z0-9-]+\.trycloudflare\.com)') {
        Set-Content -Path $marker -Value $Matches[1] -Encoding ascii
        Write-Host "public MCP endpoint: $($Matches[1])/mcp"
    }
}
