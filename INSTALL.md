# Installation Guide

## Python-only install

This is the recommended default for PyPI/TestPyPI and for users who only need
SetAnubis Python APIs or CMND-card generation:

```bash
python -m pip install .
setanubis-pythia-smoke
```

No Pythia8 or HepMC3 installation is required for this mode.

## Optional Pythia/HepMC3 runtime

Running Pythia from Python requires the optional native extension
`SetAnubis.core.Pythia.bindings.pythia_sim`.  Build it explicitly during
installation:

```bash
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
python -m pip install .[pythia]
```

Then verify:

```bash
setanubis-pythia-check
```

## Installing local external dependencies

If Pythia8/HepMC3 are not already installed, use the explicit developer helper
scripts first:

```bash
./External_Integration/install.sh HepMC3 Pythia

SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
python -m pip install .[pythia]
```

Required system tools for the external builds are usually:

- `cmake`
- `make`
- `gcc`, `g++`, `gfortran`
- `curl` or `wget`
- `tar`

## Developer install

```bash
python -m pip install -e .[dev]
pytest -q setanubis/tests/unit/pythia
```

For the optional runtime tests, compile the Pythia extension first and then run:

```bash
setanubis-pythia-smoke --run-pythia --cmnd path/to/card.cmnd --events 10
```

See `PYTHIA_PACKAGING.md` for the full native-extension packaging policy.
