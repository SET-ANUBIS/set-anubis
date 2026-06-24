# Build the standalone Pythia runner and the optional Python binding.
#
# Default paths keep the previous in-tree workflow, but every external dependency
# can now be overridden, e.g.
#
#   make PYTHIA8_DIR=/opt/pythia8 HEPMC3_DIR=/opt/hepmc3
#   make PYTHON=python3.11 install-python-module

SHELL := /usr/bin/env bash
ROOT_DIR := $(CURDIR)
BUILD_DIR ?= $(ROOT_DIR)/build

PYTHON ?= python3
CXX ?= g++
CXX_VERSION := $(shell $(CXX) -dumpversion)
MIN_GCC_VERSION := 5.0

# Dependency prefixes.  These may point either to the bundled installs produced
# by install.sh or to external system/user installations.
PYTHIA8_DIR ?= $(ROOT_DIR)/pythia8315
HEPMC3_DIR ?= $(ROOT_DIR)/../HepMC3/hepmc3-install

PYTHIA8_INCLUDE ?= $(PYTHIA8_DIR)/include
PYTHIA8_LIB ?= $(PYTHIA8_DIR)/lib
HEPMC3_INCLUDE ?= $(HEPMC3_DIR)/include
HEPMC3_LIB ?= $(HEPMC3_DIR)/lib

PYTHON_INCLUDE := $(shell $(PYTHON) -m pybind11 --includes 2>/dev/null)
PYTHON_EXT_SUFFIX := $(shell $(PYTHON)-config --extension-suffix 2>/dev/null || echo .so)

CXX_STANDARD ?= -std=c++14
CXX_WARNINGS ?= -pedantic -W -Wall -Wshadow
CXX_OPT ?= -O2 -g
CXX_COMMON := $(CXX_OPT) $(CXX_STANDARD) $(CXX_WARNINGS) -fPIC \
  -I$(PYTHIA8_INCLUDE) -I$(HEPMC3_INCLUDE) \
  -L$(PYTHIA8_LIB) -L$(HEPMC3_LIB) \
  -Wl,-rpath,$(PYTHIA8_LIB):$(HEPMC3_LIB) \
  -lpythia8 -ldl -lHepMC3
CXX_SHARED := -shared
CXX_SONAME := -Wl,-soname,
LIB_SUFFIX := .so

PYTHIA_LIB := $(PYTHIA8_LIB)/libpythia8$(LIB_SUFFIX)
PYTHON_MODULE := pythia_sim$(PYTHON_EXT_SUFFIX)
PYTHON_BINDINGS := $(ROOT_DIR)/bindings.cpp
PACKAGE_BINDINGS_DIR ?= $(ROOT_DIR)/../../setanubis/SetAnubis/core/Pythia/bindings

compare_versions = $(shell printf "$(1)\n$(2)" | sort -V | head -n 1)

ifneq ($(call compare_versions,$(CXX_VERSION),$(MIN_GCC_VERSION)),$(MIN_GCC_VERSION))
  $(error GCC version $(MIN_GCC_VERSION) or higher is required. Current version is $(CXX_VERSION).)
endif

.PHONY: all clean check-env install-python-module print-config

all: $(BUILD_DIR)/run $(BUILD_DIR)/$(PYTHON_MODULE)

print-config:
	@echo "CXX=$(CXX)"
	@echo "PYTHON=$(PYTHON)"
	@echo "PYTHIA8_DIR=$(PYTHIA8_DIR)"
	@echo "HEPMC3_DIR=$(HEPMC3_DIR)"
	@echo "PYTHON_MODULE=$(PYTHON_MODULE)"
	@echo "PACKAGE_BINDINGS_DIR=$(PACKAGE_BINDINGS_DIR)"

check-env:
	@test -d "$(PYTHIA8_INCLUDE)" || { echo "Missing Pythia8 include dir: $(PYTHIA8_INCLUDE)"; exit 1; }
	@test -f "$(PYTHIA_LIB)" || { echo "Missing Pythia8 library: $(PYTHIA_LIB)"; exit 1; }
	@test -d "$(HEPMC3_INCLUDE)" || { echo "Missing HepMC3 include dir: $(HEPMC3_INCLUDE)"; exit 1; }
	@test -d "$(HEPMC3_LIB)" || { echo "Missing HepMC3 lib dir: $(HEPMC3_LIB)"; exit 1; }
	@test -n "$(PYTHON_INCLUDE)" || { echo "pybind11 is not available for $(PYTHON). Install pybind11 first."; exit 1; }
	@echo "Pythia build environment looks OK."

$(BUILD_DIR)/run: $(ROOT_DIR)/run_hep.cpp | check-env
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(ROOT_DIR)/run_hep.cpp -o $@ $(CXX_COMMON)

$(BUILD_DIR)/$(PYTHON_MODULE): $(PYTHON_BINDINGS) | check-env
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(PYTHON_BINDINGS) -o $@ $(CXX_COMMON) $(CXX_SHARED) $(CXX_SONAME)$@ $(PYTHON_INCLUDE)

install-python-module: $(BUILD_DIR)/$(PYTHON_MODULE)
	@mkdir -p $(PACKAGE_BINDINGS_DIR)
	cp $(BUILD_DIR)/$(PYTHON_MODULE) $(PACKAGE_BINDINGS_DIR)/
	@touch $(PACKAGE_BINDINGS_DIR)/__init__.py
	@echo "Installed $(PYTHON_MODULE) into $(PACKAGE_BINDINGS_DIR)"

clean:
	rm -rf $(BUILD_DIR)
