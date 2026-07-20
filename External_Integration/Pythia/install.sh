#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${PYTHIA8_VERSION:-8315}"
PREFIX="${PYTHIA8_PREFIX:-$SCRIPT_DIR/pythia$VERSION}"
HEPMC3_PREFIX="${HEPMC3_PREFIX:-$SCRIPT_DIR/../HepMC3/hepmc3-install}"
ARCHIVE="$SCRIPT_DIR/pythia$VERSION.tgz"
SRC_DIR="$SCRIPT_DIR/pythia$VERSION-src"
DEFAULT_URL="https://www.pythia.org/download/pythia83/pythia$VERSION.tgz"
DEFAULT_FALLBACK_URL="https://gitlab.com/Pythia8/releases/-/archive/pythia$VERSION/releases-pythia$VERSION.tar.gz"
URL="${PYTHIA8_URL:-$DEFAULT_URL}"
if [[ -n "${PYTHIA8_URL:-}" ]]; then
  FALLBACK_URL="${PYTHIA8_FALLBACK_URL:-}"
else
  FALLBACK_URL="${PYTHIA8_FALLBACK_URL:-$DEFAULT_FALLBACK_URL}"
fi
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required tool: $1" >&2
    exit 1
  }
}

archive_is_valid() {
  [[ -s "$1" ]] && tar -tzf "$1" >/dev/null 2>&1
}

download_url() {
  local url="$1"
  local destination="$2"

  if command -v curl >/dev/null 2>&1; then
    curl \
      --fail \
      --location \
      --show-error \
      --retry 5 \
      --retry-all-errors \
      --retry-delay 2 \
      --connect-timeout 30 \
      --output "$destination" \
      "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget \
      --tries=5 \
      --timeout=30 \
      --output-document="$destination" \
      "$url"
  else
    echo "Missing curl or wget" >&2
    exit 1
  fi
}

download() {
  local temporary_archive="${ARCHIVE}.tmp"
  local -a urls=("$URL")
  local candidate

  if [[ -n "$FALLBACK_URL" && "$FALLBACK_URL" != "$URL" ]]; then
    urls+=("$FALLBACK_URL")
  fi

  rm -f "$temporary_archive"

  for candidate in "${urls[@]}"; do
    echo "Downloading $candidate"
    if download_url "$candidate" "$temporary_archive"; then
      if archive_is_valid "$temporary_archive"; then
        mv "$temporary_archive" "$ARCHIVE"
        return 0
      fi
      echo "Downloaded file is not a valid gzip-compressed tar archive: $candidate" >&2
      echo "Downloaded size: $(wc -c < "$temporary_archive") bytes" >&2
    else
      echo "Download failed: $candidate" >&2
    fi
    rm -f "$temporary_archive"
  done

  echo "Unable to download a valid Pythia8 $VERSION source archive." >&2
  exit 1
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

if [[ -f "$ARCHIVE" ]] && ! archive_is_valid "$ARCHIVE"; then
  echo "Removing invalid cached archive: $ARCHIVE" >&2
  rm -f "$ARCHIVE"
fi

if [[ ! -f "$ARCHIVE" ]]; then
  download
fi

rm -rf "$SRC_DIR"
mkdir -p "$SRC_DIR"
tar -xzf "$ARCHIVE" -C "$SRC_DIR" --strip-components=1

if [[ ! -x "$SRC_DIR/configure" ]]; then
  echo "Pythia configure script not found after extracting $ARCHIVE" >&2
  exit 1
fi

pushd "$SRC_DIR" >/dev/null
./configure --prefix="$PREFIX" --with-hepmc3="$HEPMC3_PREFIX"
make -j"$JOBS"
make install
popd >/dev/null

echo "Pythia8 installed successfully at $PREFIX"
echo "For SetAnubis builds, use: export SETANUBIS_PYTHIA8_DIR=$PREFIX"
