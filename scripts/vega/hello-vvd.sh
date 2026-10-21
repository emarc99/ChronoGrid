#!/usr/bin/env bash
# build the stock React Native hello world and run it on the already-booted VVD
source ~/vega/env
cd ~ && rm -rf chronohello
vega project generate --template helloWorld --name chronohello --packageId com.emarc99.chronohello --outputDir chronohello | tail -2
cd chronohello
npm install --no-audit --no-fund 2>&1 | tail -2
npx react-native build-vega --build-type Release --target x86_64 2>&1 | tail -3
ls build/x86_64-release/
vega device list 2>&1 | tail -3
vega run-app build/x86_64-release/chronohello_x86_64.vpkg com.emarc99.chronohello.main -d VirtualDevice 2>&1 | tail -5
sleep 10
vega device is-app-running --appName com.emarc99.chronohello.main -d VirtualDevice 2>&1 | tail -2
echo "=== HELLO DONE ==="
