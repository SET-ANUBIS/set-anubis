# Pythia/HepMC3 packaging policy

The SET-ANUBIS Python package is installable without Pythia8 or HepMC3.  The
native `pythia_sim` extension is compiled only when explicitly requested.

## Why opt-in?

Pythia8 and HepMC3 are external C++ packages. They are large, system-dependent
and often installed by an experiment software stack, CVMFS, a local prefix or a
container. Silent downloads during `pip install` make builds fragile and are not
appropriate for a clean PyPI release.

## Build modes

### Pure Python, default

```bash
python -m pip install SetAnubis
```

This installs the public Python API and CMND-generation tooling. It does not
compile or import `pythia_sim` at install time.

### Native Pythia runtime

```bash
SETANUBIS_BUILD_PYTHIA=1 SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"
```

For editable development:

```bash
SETANUBIS_BUILD_PYTHIA=1 SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install python -m pip install -e ".[pythia]"
```

## Environment variables

| Variable | Meaning |
| --- | --- |
| `SETANUBIS_BUILD_PYTHIA=1` | Force compilation of the optional extension. |
| `SETANUBIS_BUILD_PYTHIA=auto` | Compile only if all dependencies are detected. |
| `SETANUBIS_PYTHIA8_DIR` | Pythia8 install prefix. |
| `SETANUBIS_PYTHIA8_INCLUDE` | Pythia8 include directory override. |
| `SETANUBIS_PYTHIA8_LIB` | Pythia8 library directory override. |
| `SETANUBIS_HEPMC3_DIR` | HepMC3 install prefix. |
| `SETANUBIS_HEPMC3_INCLUDE` | HepMC3 include directory override. |
| `SETANUBIS_HEPMC3_LIB` | HepMC3 library directory override. |

The build also checks `pythia8-config --prefix` and `HepMC3-config --prefix` if
those commands are on `PATH`.

## TestPyPI and PyPI release flow

1. Update `pyproject.toml`, `SetAnubis/_version.py`, `CHANGELOG.md` and
   `CITATION.cff`.
2. Run local checks:

   ```bash
   python -m pip install -e ".[dev,docs]"
   python -m pytest -q setanubis/tests
   python -m build
   twine check dist/*
   ```

3. Use the `Release` GitHub workflow with `repository=testpypi`.
4. Install from TestPyPI in a clean environment.
5. Tag the release:

   ```bash
   git tag -a v1.0.0 -m "SetAnubis 1.0.0"
   git push origin v1.0.0
   ```

The tag publishes to PyPI through Trusted Publishing once the PyPI project has a
matching trusted publisher configured for this repository and workflow.

## Wheel policy

Official PyPI wheels are Python-only by default. Users needing the native Pythia
runtime should install from source with `--no-binary SetAnubis` and explicit
external dependency paths. This avoids distributing wheels tied to a particular
Pythia/HepMC3 ABI.
