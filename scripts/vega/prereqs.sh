#!/usr/bin/env bash
# run as root inside WSL: KVM access + Vega SDK prerequisites
set -e
export DEBIAN_FRONTEND=noninteractive
U="${SUDO_USER:-$USER}"

groupadd -f kvm
chown root:kvm /dev/kvm
chmod 660 /dev/kvm
usermod -aG kvm "$U"
echo kvm_intel > /etc/modules-load.d/kvm.conf
echo 'KERNEL=="kvm", GROUP="kvm", MODE="0660"' > /etc/udev/rules.d/99-kvm.rules

if snap list curl >/dev/null 2>&1; then snap remove curl; fi
apt-get update -qq
apt-get install -y -qq curl lz4 watchman software-properties-common qemu-kvm libvirt-daemon-system cpu-checker >/dev/null
apt-get install -y -qq libpython3.8-dev >/dev/null 2>&1 || echo "skip libpython3.8-dev (only for crash symbolication)"

if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 18 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null
  apt-get install -y -qq nodejs >/dev/null
fi
usermod -aG libvirt "$U" || true

echo "--- prereqs ok"
kvm-ok || true
node --version
ls -l /dev/kvm
