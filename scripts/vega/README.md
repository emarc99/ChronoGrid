# Vega Virtual Device on Windows (WSL2)

Known-good on Windows 11 + WSL2 Ubuntu 24.04 with an Intel CPU, Vega SDK 0.24.12112.

```powershell
# 1. KVM access + prerequisites (runs as root, no sudo prompt)
wsl -d Ubuntu-24.04 -u root -e env SUDO_USER=<your-wsl-user> bash scripts/vega/prereqs.sh
# 2. Vega CLI + SDK + VVD, non-interactive (~15 min)
wsl -d Ubuntu-24.04 -e bash scripts/vega/install-sdk.sh
# 3. Boot the VVD, build the stock helloWorld app, install and launch it.
#    The VVD dies when the shell that started it exits, so keep this session open.
wsl -d Ubuntu-24.04 -e bash -lc "source ~/vega/env && vega virtual-device start && bash scripts/vega/hello-vvd.sh && sleep infinity"
```

If a boot fails with "failed to access shell", run `scripts/vega/diag-vvd.sh`, then delete the instance under `~/vega/sdk/vega-sdk/main/<version>/vvd/instances/` and start again.

The VVD can't install `vegaWebview` apps (missing `webview_4` module); use a React Native template.
