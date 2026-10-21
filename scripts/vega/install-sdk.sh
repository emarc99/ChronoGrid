#!/usr/bin/env bash
# run as the normal user inside WSL
set -e
export NONINTERACTIVE=true
curl -fsSL https://sdk-installer.vega.labcollab.net/get_vvm.sh | bash
source ~/vega/env
vega --version
