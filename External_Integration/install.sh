#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage: External_Integration/install.sh [HepMC3] [Pythia] [MadGraph] [Marty]

Examples:
  External_Integration/install.sh HepMC3 Pythia
  HEPMC3_PREFIX=/opt/hepmc3 PYTHIA8_PREFIX=/opt/pythia8 External_Integration/install.sh HepMC3 Pythia
EOF
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

command_exists() { command -v "$1" >/dev/null 2>&1; }

required_tools=(cmake gcc gfortran g++ make)
for tool in "${required_tools[@]}"; do
  if ! command_exists "$tool"; then
    echo "Missing build tool: $tool" >&2
    echo "Install your platform build essentials first, then rerun this script." >&2
    exit 1
  fi
done

declare -A deps=(
  [Pythia]="HepMC3"
  [HepMC3]=""
  [MadGraph]=""
  [Marty]=""
)

resolved=()
visiting=()

contains() {
  local needle="$1"; shift
  local item
  for item in "$@"; do [[ "$item" == "$needle" ]] && return 0; done
  return 1
}

resolve() {
  local item="$1"
  if [[ -z "${deps[$item]+set}" ]]; then
    echo "Unknown external integration: $item" >&2
    exit 1
  fi
  contains "$item" "${resolved[@]}" && return 0
  if contains "$item" "${visiting[@]}"; then
    echo "Circular dependency involving $item" >&2
    exit 1
  fi
  visiting+=("$item")
  local dep
  for dep in ${deps[$item]}; do
    resolve "$dep"
  done
  resolved+=("$item")
}

for requested in "$@"; do
  resolve "$requested"
done

for software in "${resolved[@]}"; do
  echo "Installing $software..."
  (cd "$SCRIPT_DIR/$software" && ./install.sh)
done

echo "Installed external integrations: ${resolved[*]}"
