# Installation

SET-ANUBIS supports two installation modes:

1. **Python-only**: the default, portable install for model/card handling,
   branching-ratio interfaces, geometry, selection utilities and CMND generation.
2. **Python + native Pythia binding**: an explicit build that links against
   external Pythia8 and HepMC3 installations.

## Requirements

- Python 3.10, 3.11 or 3.12
- Linux or WSL for the full event-generation stack
- C++ compiler, CMake, Make and `gfortran` for optional external tools
- Optional: Docker for MadGraph workflows that use containers

## Python-only install

```bash
python -m pip install SetAnubis
```

From a checkout:

```bash
git clone https://github.com/SET-ANUBIS/set-anubis.git
cd set-anubis
python -m pip install -e .
setanubis-pythia-smoke
```

## Developer install

```bash
python -m pip install -e ".[dev,docs]"
python -m pytest -q setanubis/tests
sphinx-build -b html Docs/manual/source Docs/manual/build/html
```

## Optional Pythia/HepMC3 binding

The binding is intentionally opt-in. This keeps normal PyPI installs fast and
avoids silently compiling large C++ packages on user machines.

### Use external installations

```bash
SETANUBIS_BUILD_PYTHIA=1 SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"
```

When installing from a local checkout, use `python -m pip install -e ".[pythia]"`
instead of the PyPI package name.

### Build local external tools from the checkout

```bash
./External_Integration/install.sh HepMC3 Pythia
SETANUBIS_BUILD_PYTHIA=1 SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install python -m pip install -e ".[pythia]"
```

### Diagnostics

```bash
setanubis-pythia-check
```

This reports whether the Python binding is importable and where Pythia8/HepMC3
were found.

## MadGraph

MadGraph can be installed through the external helper or used via a local path /
Docker runner depending on your workflow:

```bash
./External_Integration/install.sh MadGraph
python -m pip install -e ".[madgraph]"
```

## GUI extras

```bash
python -m pip install "SetAnubis[app]"
```

Then see the GUI-specific READMEs:

- `setanubis/SetAnubis/HepMCGUI/README.md`
- `setanubis/SetAnubis/SetAnubisDBDashboard/README.md`

## Troubleshooting

- `ModuleNotFoundError: pythia_sim`: the optional native binding was not built.
  Run `setanubis-pythia-check` and rebuild with `SETANUBIS_BUILD_PYTHIA=1`.
- `Pythia8/Pythia.h` not found: set `SETANUBIS_PYTHIA8_DIR` or
  `SETANUBIS_PYTHIA8_INCLUDE`.
- `HepMC3/GenEvent.h` not found: set `SETANUBIS_HEPMC3_DIR` or
  `SETANUBIS_HEPMC3_INCLUDE`.
- Large assets are not shipped inside the wheel. Use absolute paths or set
  `SETANUBIS_ASSETS_DIR=/path/to/Assets` for private UFOs and samples.
