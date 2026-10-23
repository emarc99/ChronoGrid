#!/usr/bin/env bash
# Expose ChronoGrid's MCP endpoint to the cloud (AgentCore Runtime) through a Cloudflare quick tunnel (macOS/Linux).
# Only /mcp with the bearer token is reachable through it (see tunnel_guard in server/api.py).
#   ./scripts/tunnel.sh [port]
set -euo pipefail
cd "$(dirname "$0")/.."
port="${1:-8787}"

exe=$(command -v cloudflared || true)
if [ -z "$exe" ]; then
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) asset=cloudflared-linux-amd64 ;;
    Linux-aarch64 | Linux-arm64) asset=cloudflared-linux-arm64 ;;
    *) echo "Install cloudflared first (macOS: brew install cloudflared)" >&2; exit 1 ;;
  esac
  exe=tools/cloudflared
  if [ ! -x "$exe" ]; then
    mkdir -p tools
    curl -fsSL -o "$exe" "https://github.com/cloudflare/cloudflared/releases/latest/download/$asset"
    chmod +x "$exe"
  fi
fi

marker=data/public_url.txt
mkdir -p data
rm -f "$marker"

"$exe" tunnel --no-autoupdate --url "http://127.0.0.1:$port" 2>&1 | while IFS= read -r line; do
  echo "$line"
  if [[ "$line" =~ (https://[a-z0-9-]+\.trycloudflare\.com) ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}" > "$marker"
    echo "public MCP endpoint: ${BASH_REMATCH[1]}/mcp"
  fi
done
