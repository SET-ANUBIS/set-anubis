#!/bin/bash

command -v cmake >/dev/null 2>&1 || { echo >&2 "CMake is not installed. Stop."; exit 1; }


HEPMC3_DIR="../HepMC3/hepmc3-install"

if [[ ! -d "$HEPMC3_DIR" ]]; then
    echo "HepMC3 must be installed before Pythia. Stop."
    exit 1
fi

PYTHIA_SOURCE_DIR="pythia8315"

echo "Downloading Pythia..."
wget -O pythia8315.tar.gz https://www.pythia.org/download/pythia83/pythia8315.tgz

echo "Extraction of Pythia..."
tar -xzf pythia8315.tar.gz

cd pythia8315

echo "Configuration of Pythia..."
./configure --with-hepmc3=$HEPMC3_DIR \
    #   --with-python \

echo "Compilation de Pythia..."
make

echo "Installation of Pythia..."
make install


echo "Pythia installed with success."

cd ..

make

TARGET_PATH="$(pwd)/build"

BASHRC_FILE="$HOME/.bashrc"

if ! grep -q "PYTHONPATH=.*$TARGET_PATH" "$BASHRC_FILE"; then
    echo "Ajout de '$TARGET_PATH' à PYTHONPATH dans $BASHRC_FILE"
    echo "export PYTHONPATH=\$PYTHONPATH:$TARGET_PATH" >> "$BASHRC_FILE"
    source "$BASHRC_FILE"
else
    echo "'$TARGET_PATH' est déjà dans PYTHONPATH"
fi
