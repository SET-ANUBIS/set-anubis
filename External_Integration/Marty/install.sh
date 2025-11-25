#!/bin/bash
set -e

# === Variables ===
ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_DIR="$ROOT_DIR/MARTY_INSTALL"
SRC_DIR="$ROOT_DIR/src"
MARTY_REPO="https://github.com/docbrown1955/marty-public.git"
MARTY_TAG="1.6-beta"
CLONE_DIR="$SRC_DIR/MARTY"

# === Étape 1 : Clonage du dépôt Marty ===
echo "📦 Cloning Marty (if not already present)..."
if [[ ! -d "$CLONE_DIR" ]]; then
    mkdir -p "$SRC_DIR"
    git clone --branch "$MARTY_TAG" "$MARTY_REPO" "$CLONE_DIR"
else
    echo "✅ Marty repo already cloned."
fi

# === Étape 2 : Patch du CMakeLists.txt (set C++20) ===
echo "🛠️  Applying C++20 patch..."
sed -i 's/set(CMAKE_CXX_STANDARD 17)/set(CMAKE_CXX_STANDARD 20)/' "$SRC_DIR/CMakeLists.txt" || true

# === Étape 3 : Création du build directory ===
echo "🏗️  Configuring Marty..."
mkdir -p "$CLONE_DIR/build"
cd "$CLONE_DIR/build"

cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR"

# === Étape 4 : Patchs Marty source ===
echo "🩹 Patching Marty sources..."
patch_files=(
    "src/csl/abreviation.h"
    "src/csl/diagonalization.h"
    "src/csl/hardFactor.h"
    "src/csl/index.h"
    "src/csl/replace.h"
    "src/csl/variableParent.cpp"
    "src/csl/variableParent.h"
    "src/grafed/core/latexLink.h"
    "src/grafed/gui/latexLink.h"
)

for f in "${patch_files[@]}"; do
    full_path="$CLONE_DIR/$f"
    if [[ -f "$full_path" ]]; then
        sed -i '1i #include <algorithm>' "$full_path"
    fi
done

# Patch spécifique : add <type_traits> + parent.h in replace.h
replace_header="$CLONE_DIR/src/csl/replace.h"
if [[ -f "$replace_header" ]]; then
    sed -i 's|#include "abstract.h"|#include <type_traits>\n#include "parent.h"\n#include "abstract.h"|' "$replace_header"
fi

# Patch find_if → std::find_if
findif_patch="$CLONE_DIR/src/csl/variableParent.cpp"
if [[ -f "$findif_patch" ]]; then
    sed -i 's/\([^:]\)\bfind_if\b/\1std::find_if/g' "$findif_patch"
fi

# === Étape 5 : Compilation ===
echo "🔨 Building Marty..."
make -j"$(nproc)"

# === Étape 6 : Installation ===
echo "📦 Installing Marty..."
make install

# === Étape 7 : Mise à jour du .bashrc ===
echo "🔧 Updating environment variables in ~/.bashrc..."
bashrc_file="$HOME/.bashrc"

env_vars=(
    "PATH=\$PATH:$INSTALL_DIR/bin"
    "CPATH=\$CPATH:$INSTALL_DIR/include"
    "C_INCLUDE_PATH=\$C_INCLUDE_PATH:$INSTALL_DIR/include"
    "LIBRARY_PATH=\$LIBRARY_PATH:$INSTALL_DIR/lib"
    "LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$INSTALL_DIR/lib"
)

for var in "${env_vars[@]}"; do
    export_line="export $var"
    if ! grep -Fxq "$export_line" "$bashrc_file"; then
        echo "$export_line" >> "$bashrc_file"
    fi
done

# === Étape 8 : Vérification finale ===
echo "✅ Sourcing .bashrc..."
source "$bashrc_file"

if [[ -f "$INSTALL_DIR/lib/libmarty.so" ]]; then
    echo "🎉 Marty successfully installed at $INSTALL_DIR"
else
    echo "❌ ERROR: Marty installation failed. libmarty.so not found."
    exit 1
fi
