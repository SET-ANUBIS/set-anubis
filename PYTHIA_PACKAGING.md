# Pythia/HepMC3 packaging and installation

SetAnubis now treats the Pythia runtime as an **optional native extension**.
The pure-Python package can be installed without Pythia8/HepMC3, which is the
right default for PyPI.  CMND-card generation remains usable in this mode.

The C++/pybind11 extension is compiled only when explicitly requested.

## 1. Python-only install

```bash
python -m pip install .
setanubis-pythia-check
setanubis-pythia-smoke
```

`setanubis-pythia-check` should report that the Python binding is missing, but
this is expected for a Python-only install.

## 2. Use existing Pythia8/HepMC3 installations

If Pythia8 and HepMC3 are already installed, point the build at their prefixes:

```bash
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
python -m pip install .[pythia]
```

Optional overrides are also supported:

```bash
SETANUBIS_PYTHIA8_INCLUDE=/path/to/pythia8/include
SETANUBIS_PYTHIA8_LIB=/path/to/pythia8/lib
SETANUBIS_HEPMC3_INCLUDE=/path/to/hepmc3/include
SETANUBIS_HEPMC3_LIB=/path/to/hepmc3/lib
```

After installation:

```bash
setanubis-pythia-check
setanubis-pythia-smoke --run-pythia --cmnd path/to/card.cmnd --events 10
```


### Important note about published wheels

If a pure-Python wheel is published on PyPI, `pip install SetAnubis[pythia]` will
prefer that wheel and will **not** compile `pythia_sim`.  Users who want to
compile the binding from the published source distribution must force a source
build, for example:

```bash
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
python -m pip install --no-binary SetAnubis SetAnubis[pythia]
```

From a git checkout, `python -m pip install .[pythia]` already builds from
source, so `--no-binary` is not needed.

## 3. Install bundled external dependencies first

For development machines where Pythia8/HepMC3 are not installed, use the
external integration scripts explicitly, then build the Python extension:

```bash
./External_Integration/install.sh HepMC3 Pythia

SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
python -m pip install .[pythia]
```

The dependency installers are intentionally not run automatically by `pip`.
They download and compile large external projects, may require system build
tools, and are not appropriate as hidden side effects of PyPI installation.

## 4. Editable development workflow

```bash
python -m pip install -e .[dev,pythia]
./External_Integration/install.sh HepMC3 Pythia
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
python -m pip install -e .[pythia]
pytest -q setanubis/tests/unit/pythia
```

## 5. TestPyPI/PyPI recommendation

Publish the default wheel as Python-only first.  Users who need event generation
can either compile from source with `SETANUBIS_BUILD_PYTHIA=1`, or you can later
publish platform-specific wheels built in CI against a controlled Pythia/HepMC3
stack.

The recommended project policy is:

- PyPI default: no native Pythia dependency, no downloads during install.
- Source install with explicit paths: supported.
- In-repo dependency bootstrap scripts: supported for developers, explicit only.
- Binary wheels with bundled/linked native libraries: future CI work, with
  license and auditwheel/delocate checks.
