#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${HEPMC3_VERSION:-3.2.6}"
PREFIX="${HEPMC3_PREFIX:-$SCRIPT_DIR/hepmc3-install}"
SRC_ARCHIVE="$SCRIPT_DIR/HepMC3-$VERSION.tar.gz"
SRC_DIR="$SCRIPT_DIR/HepMC3-$VERSION"
BUILD_DIR="$SCRIPT_DIR/hepmc3-build"
URL="${HEPMC3_URL:-https://hepmc.web.cern.ch/hepmc/releases/HepMC3-$VERSION.tar.gz}"
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required tool: $1" >&2
    exit 1
  }
}

download() {
  if command -v curl >/dev/null 2>&1; then
    curl -L "$URL" -o "$SRC_ARCHIVE"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$SRC_ARCHIVE" "$URL"
  else
    echo "Missing curl or wget" >&2
    exit 1
  fi
}

need cmake
need make
need tar

echo "Installing HepMC3 $VERSION into $PREFIX"
mkdir -p "$SCRIPT_DIR"

if [[ ! -f "$SRC_ARCHIVE" ]]; then
  echo "Downloading $URL"
  download
fi

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Extracting $SRC_ARCHIVE"
  tar -xzf "$SRC_ARCHIVE" -C "$SCRIPT_DIR"
fi

cmake -S "$SRC_DIR" -B "$BUILD_DIR" \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DHEPMC3_ENABLE_ROOTIO:BOOL=OFF \
  -DHEPMC3_ENABLE_PROTOBUFIO:BOOL=OFF \
  -DHEPMC3_ENABLE_TEST:BOOL=OFF \
  -DHEPMC3_INSTALL_INTERFACES:BOOL=ON \
  -DHEPMC3_BUILD_STATIC_LIBS:BOOL=OFF \
  -DHEPMC3_BUILD_DOCS:BOOL=OFF \
  -DHEPMC3_ENABLE_PYTHON:BOOL=OFF

cmake --build "$BUILD_DIR" --parallel "$JOBS"
cmake --install "$BUILD_DIR"

echo "HepMC3 installed successfully at $PREFIX"
echo "For SetAnubis builds, use: export SETANUBIS_HEPMC3_DIR=$PREFIX"
