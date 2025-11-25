#!/usr/bin/env bash
set -euo pipefail


# Check Linux distribution


if [[ ! -r /etc/os-release ]]; then
    echo "Cannot detect Linux distribution (/etc/os-release missing)."
    exit 1
fi

. /etc/os-release

# Explicitly reject Ubuntu & Debian
if [[ "${ID:-}" == "ubuntu" || "${ID_LIKE:-}" == *"debian"* ]]; then
    echo "Error: this installation script does not support Ubuntu/Debian."
    echo "Please use a Fedora/RHEL/AlmaLinux-type distribution."
    exit 1
fi

# Positive check: Fedora & RHEL-like (Fedora, RHEL, AlmaLinux, CentOS, etc.)
if [[ "${ID:-}" != "fedora" && "${ID_LIKE:-}" != *"rhel"* && "${ID_LIKE:-}" != *"fedora"* ]]; then
    echo "Warning: untested distribution: ${PRETTY_NAME:-unknown}"
    echo "This script is intended for Fedora / RHEL / AlmaLinux / CentOS."
fi

# Check required packages

echo "Checking required packages..."

required_pkgs=(gcc-gfortran cmake gcc-c++ rsync)
missing=()

for pkg in "${required_pkgs[@]}"; do
    if ! rpm -q "$pkg" &>/dev/null; then
        missing+=("$pkg")
    fi
done

if ((${#missing[@]})); then
    echo "Error: the following packages are missing: ${missing[*]}"
    echo "Install them for example with:"
    echo "  sudo dnf install ${missing[*]}"
    exit 1
fi

echo "OK: all required packages are installed."

# Download and extract MadGraph

echo "Downloading MadGraph..."
TARBALL_URL="https://launchpad.net/mg5amcnlo/3.0/3.5.x/+download/MG5_aMC_v3.5.8.tar.gz"
TARBALL_NAME="madgraph.tar.gz"
MG_DIR="MG5_aMC_v3_5_8"

wget -O "$TARBALL_NAME" "$TARBALL_URL"

echo "Extracting MadGraph..."
tar -xzpvf "$TARBALL_NAME"

# Run mg5_aMC and install LHAPDF6 + Pythia8

echo "Running mg5_aMC to install LHAPDF6 and Pythia8..."

cd "$MG_DIR"

# Send commands to mg5_aMC via a here-doc
./bin/mg5_aMC <<'EOF'
install lhapdf6
install pythia8
quit
EOF

echo "MadGraph + LHAPDF6 + Pythia8 installation completed."
