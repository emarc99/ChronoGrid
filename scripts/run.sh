#!/usr/bin/env bash
# Start ChronoGrid (MCP server + API + ambient screen) on http://127.0.0.1:8787 (macOS/Linux)
#   ./scripts/run.sh             # build the web UI if needed and start
#   ./scripts/run.sh --seed      # also reset the ledger with demo history
#   ./scripts/run.sh --rebuild   # force a web rebuild
set -euo pipefail
cd "$(dirname "$0")/.."

seed=0
rebuild=0
for arg in "$@"; do
  case "$arg" in
    --seed) seed=1 ;;
    --rebuild) rebuild=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

python=.venv/bin/python
if [ ! -x "$python" ]; then
  python3 -m venv .venv
  "$python" -m pip install -e ".[dev]"
fi

if command -v lsof >/dev/null; then
  pids=$(lsof -ti tcp:8787 -sTCP:LISTEN || true)
  if [ -n "$pids" ]; then kill $pids; sleep 1; fi
fi

if [ "$rebuild" = 1 ] || [ ! -f web/dist/index.html ]; then
  (cd web && { [ -d node_modules ] || npm install; } && npm run build)
fi

if [ "$seed" = 1 ]; then "$python" -m seed.seed; fi
exec "$python" -m server.api
