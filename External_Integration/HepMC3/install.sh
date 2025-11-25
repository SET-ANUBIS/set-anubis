#!/bin/bash

command -v cmake >/dev/null 2>&1 || { echo >&2 "CMake is not installed. Stop."; exit 1; }
command -v wget >/dev/null 2>&1 || { echo >&2 "wget is not installed. Stop."; exit 1; }

echo "Downloading of HepMC3..."
wget -O HepMC3-3.2.6.tar.gz http://hepmc.web.cern.ch/hepmc/releases/HepMC3-3.2.6.tar.gz

echo "Extraction of HepMC3..."
tar -xzf HepMC3-3.2.6.tar.gz

# Création du répertoire de build
mkdir -p hepmc3-build
cd hepmc3-build

# Configuration et build
echo "Configuration of HepMC3..."
cmake -DCMAKE_INSTALL_PREFIX=../hepmc3-install \
      -DHEPMC3_ENABLE_ROOTIO:BOOL=OFF \
      -DHEPMC3_ENABLE_PROTOBUFIO:BOOL=OFF \
      -DHEPMC3_ENABLE_TEST:BOOL=OFF \
      -DHEPMC3_INSTALL_INTERFACES:BOOL=ON \
      -DHEPMC3_BUILD_STATIC_LIBS:BOOL=OFF \
      -DHEPMC3_BUILD_DOCS:BOOL=OFF \
      -DHEPMC3_ENABLE_PYTHON:BOOL=ON \
      -DHEPMC3_PYTHON_VERSIONS=3.12 \
      -DHEPMC3_Python_SITEARCH312=../hepmc3-install/lib/python3.12/site-packages \
      ../HepMC3-3.2.6

# Compilation
echo "Compilation of HepMC3..."
make

# Installation
echo "Installation of HepMC3..."
make install

echo "HepMC3 installed with success."
