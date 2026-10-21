#!/usr/bin/env bash
pkill -f '^kvm' 2>/dev/null
V=~/vega/sdk/vega-sdk/main/0.24.12112/vvd
grep -n -i -E 'error|fail|panic|unresponsive|ready|deadline' $V/virtual_device.log | tail -25 | cut -c1-260
echo '--- instances'
ls -t $V/instances/ | head
I=$(ls -td $V/instances/*/ | head -1)
ls -la "$I" | head -30
for f in "$I"/*.log "$I"/*/*.log; do [ -f "$f" ] && { echo "--- $f"; tail -15 "$f" | cut -c1-220; }; done
