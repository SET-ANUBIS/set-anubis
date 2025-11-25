# Set the shell.
SHELL=/usr/bin/env bash

# Root directory (absolute path)
ROOT_DIR:=$(CURDIR)

# Build directory (absolute path)
BUILD_DIR=$(ROOT_DIR)/build

# Install directory prefixes (absolute paths).
PREFIX_BIN=$(ROOT_DIR)/pythia8315/bin
PREFIX_INCLUDE=$(ROOT_DIR)/pythia8315/include
PREFIX_LIB=$(ROOT_DIR)/pythia8315/lib
PREFIX_SHARE=$(ROOT_DIR)/pythia8315/share/Pythia8

# HepMC3 install directory prefix (absolute path)
HEPMC3_INSTALL_DIR=$(ROOT_DIR)/../HepMC3/hepmc3-install

# Compilation flags
CXX=g++
CXX_VERSION=$(shell $(CXX) -dumpversion)
CXX_STANDARD=-std=c++14 # Ensure using at least C++14
CXX_COMMON=-O2 -g -std=c++14 -pedantic -W -Wall -Wshadow -fPIC -I$(PREFIX_INCLUDE) -I$(HEPMC3_INSTALL_DIR)/include $(GZIP_LIB)
CXX_COMMON+= -L$(PREFIX_LIB) -L$(HEPMC3_INSTALL_DIR)/lib -Wl,-rpath,$(PREFIX_LIB):$(HEPMC3_INSTALL_DIR)/lib -lpythia8 -ldl -lHepMC3
CXX_SHARED=-shared
CXX_SONAME=-Wl,-soname,
LIB_SUFFIX=.so

PYTHIA=$(PREFIX_LIB)/libpythia8$(LIB_SUFFIX)

# Python bindings
PYTHON_MODULE=pythia_sim$(LIB_SUFFIX)
PYTHON_BINDINGS=$(ROOT_DIR)/bindings.cpp

PYTHON_INCLUDE=$(shell python3 -m pybind11 --includes)

MIN_GCC_VERSION=5.0

compare_versions = $(shell printf "$(1)\n$(2)" | sort -V | head -n 1)

# Check GCC version
ifneq ($(call compare_versions,$(CXX_VERSION),$(MIN_GCC_VERSION)),$(MIN_GCC_VERSION))
  $(error "GCC version $(MIN_GCC_VERSION) or higher is required. Current version is $(CXX_VERSION).")
endif

#-----------------------#
#-- Making the runner --#
#-----------------------#

all: $(BUILD_DIR)/run $(BUILD_DIR)/$(PYTHON_MODULE)

# Compile the main C++ runner
$(BUILD_DIR)/run: $(PYTHIA) $(ROOT_DIR)/run_hep.cpp
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(ROOT_DIR)/run_hep.cpp -o $@ $(CXX_COMMON)

# Compile the Python module using pybind11
$(BUILD_DIR)/$(PYTHON_MODULE): $(PYTHIA) $(PYTHON_BINDINGS)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(PYTHON_BINDINGS) -o $@ $(CXX_COMMON) $(CXX_SHARED) $(CXX_SONAME)$@ $(PYTHON_INCLUDE)

clean:
	rm -rf $(BUILD_DIR)


