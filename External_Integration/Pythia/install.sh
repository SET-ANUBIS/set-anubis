#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${PYTHIA8_VERSION:-8315}"
PREFIX="${PYTHIA8_PREFIX:-$SCRIPT_DIR/pythia$VERSION}"
HEPMC3_PREFIX="${HEPMC3_PREFIX:-$SCRIPT_DIR/../HepMC3/hepmc3-install}"
ARCHIVE="$SCRIPT_DIR/pythia$VERSION.tgz"
SRC_DIR="$SCRIPT_DIR/pythia$VERSION-src"
URL="${PYTHIA8_URL:-https://pythia.org/download/pythia83/pythia$VERSION.tgz}"
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required tool: $1" >&2
    exit 1
  }
}

download() {
  if command -v curl >/dev/null 2>&1; then
    curl -L "$URL" -o "$ARCHIVE"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$ARCHIVE" "$URL"
  else
    echo "Missing curl or wget" >&2
    exit 1
  fi
}

need make
need tar
need g++

echo "Installing Pythia8 $VERSION into $PREFIX"
if [[ ! -d "$HEPMC3_PREFIX" ]]; then
  echo "HepMC3 prefix not found: $HEPMC3_PREFIX" >&2
  echo "Install HepMC3 first, or set HEPMC3_PREFIX=/path/to/hepmc3." >&2
  exit 1
fi

if [[ ! -f "$ARCHIVE" ]]; then
  echo "Downloading $URL"
  download
fi

rm -rf "$SRC_DIR"
mkdir -p "$SRC_DIR"
tar -xzf "$ARCHIVE" -C "$SRC_DIR" --strip-components=1

pushd "$SRC_DIR" >/dev/null
./configure --prefix="$PREFIX" --with-hepmc3="$HEPMC3_PREFIX"
make -j"$JOBS"
make install
popd >/dev/null

echo "Pythia8 installed successfully at $PREFIX"
echo "For SetAnubis builds, use: export SETANUBIS_PYTHIA8_DIR=$PREFIX"
