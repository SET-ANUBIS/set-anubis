#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./install.sh                      # install SetAnubis Python package
  ./install.sh --editable            # editable Python install
  ./install.sh --with-external HepMC3 Pythia

For the optional Pythia Python binding, install external dependencies first and
then run pip with SETANUBIS_BUILD_PYTHIA=1. See PYTHIA_PACKAGING.md.
EOF
}

editable=0
with_external=0
external_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --editable|-e)
      editable=1
      shift
      ;;
    --with-external)
      with_external=1
      shift
      external_args=("$@")
      break
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "$with_external" -eq 1 ]]; then
  "$ROOT_DIR/External_Integration/install.sh" "${external_args[@]}"
fi

if [[ "$editable" -eq 1 ]]; then
  python -m pip install -e "$ROOT_DIR"
else
  python -m pip install "$ROOT_DIR"
fi

cat <<EOF

SetAnubis Python package installed.
Run diagnostics with:
  setanubis-pythia-check

For native Pythia builds, see PYTHIA_PACKAGING.md.
EOF
