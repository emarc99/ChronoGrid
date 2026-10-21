#!/usr/bin/env bash
# Boot the Vega Virtual Device and keep it alive (it dies with the shell that started it).
source ~/vega/env
if ! vega virtual-device status 2>/dev/null | grep -q '"running":true'; then
  vega virtual-device start --timeout 180 || {
    echo "boot failed; wiping instance and retrying"
    vega virtual-device stop >/dev/null 2>&1
    rm -rf "$(dirname "$(dirname "$(command -v vega)")")"/sdk/vega-sdk/main/*/vvd/instances/*
    vega virtual-device start --timeout 180
  }
fi
echo "=== VVD UP ==="
sleep infinity
