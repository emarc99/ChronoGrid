#!/usr/bin/env bash
# Sync tv/ into the WSL filesystem, type-check, build for x86_64 and run on the VVD.
set -e
source ~/vega/env
SRC="$(cd "$(dirname "$0")/../../tv" && pwd)"
DST=~/chronotv-build
mkdir -p "$DST"
rsync -a --delete --exclude node_modules --exclude build --exclude buildinfo.json "$SRC"/ "$DST"/
cd "$DST"
if [ ! -d node_modules ]; then npm install --no-audit --no-fund; fi
npx tsc --noEmit
npx react-native build-vega --build-type Release --target x86_64 | tail -2
vega run-app build/x86_64-release/chronotv_x86_64.vpkg com.emarc99.chronotv.main -d VirtualDevice
