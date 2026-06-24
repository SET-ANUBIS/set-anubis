# SET-ANUBIS

[![CI](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/ci.yml/badge.svg)](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/ci.yml)
[![Docs](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/docs.yml/badge.svg)](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/docs.yml)
[![PyPI](https://img.shields.io/pypi/v/SetAnubis.svg)](https://pypi.org/project/SetAnubis/)
[![Python](https://img.shields.io/pypi/pyversions/SetAnubis.svg)](https://pypi.org/project/SetAnubis/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![DOI / citation](https://img.shields.io/badge/cite-arXiv%3A2512.14942-b31b1b.svg)](https://arxiv.org/abs/2512.14942)

**SET-ANUBIS** — *Simulation, accEptance and sensiTivity studies framework for
ANUBIS* — is a modular Python/C++ toolkit for long-lived-particle (LLP)
sensitivity studies for the proposed ANUBIS detector.

It connects model input, decay-width and branching-ratio calculations, event
generation, event storage, ATLAS-cavern/ANUBIS geometry, selection cutflows and
sensitivity projections through small domain APIs and replaceable adapters.

<p align="center">
  <img src="Docs/assets/set-anubis-architecture.png" alt="SET-ANUBIS architecture" width="900">
</p>

## Highlights

- **Model-agnostic UFO interface** for particle content, parameters, masses,
  widths and MadGraph-compatible cards.
- **Branching-ratio and lifetime layer** with Python, file-interpolation,
  MadGraph and MARTY-oriented adapters.
- **Event-generation adapters** for Pythia8 and MadGraph5_aMC@NLO.
- **Optional compiled Pythia/HepMC3 Python binding** that is disabled by default
  and can be built explicitly during `pip install`.
- **Geometry and selection pipeline** for ATLAS cavern / ANUBIS RPC acceptance,
  cutflows, isolation, jets and lifetime reweighting.
- **Content-addressed event database** for reproducible scans and storage-aware
  regeneration/audit workflows.
- **Dash inspection tools** for HepMC event visualisation and database auditing.

## Installation

### Python-only install

```bash
python -m pip install SetAnubis
```

From a local checkout:

```bash
git clone https://github.com/SET-ANUBIS/set-anubis.git
cd set-anubis
python -m pip install -e .
setanubis-pythia-smoke
```

The default install is pure Python. It supports the public APIs, UFO/card
manipulation and Pythia CMND generation without requiring Pythia8 or HepMC3 on
the machine.

### Optional Pythia/HepMC3 runtime

To run Pythia from Python, install or build Pythia8 and HepMC3, then compile the
optional binding explicitly:

```bash
SETANUBIS_BUILD_PYTHIA=1 SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"
```

For a local developer checkout you can use the bundled external-install helper:

```bash
./External_Integration/install.sh HepMC3 Pythia
SETANUBIS_BUILD_PYTHIA=1 SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install python -m pip install -e ".[pythia]"
```

Validate the runtime with:

```bash
setanubis-pythia-check
```

See [`PYTHIA_PACKAGING.md`](PYTHIA_PACKAGING.md) for the full packaging and
native-extension policy.

## Quick start

The 1.0.0 release exposes a short public API. Prefer `from setanubis import ...`
for user scripts and notebooks.

```python
from setanubis import SetAnubisInterface, PythiaRunInterface, ufo_path

model = SetAnubisInterface(ufo_path("UFO_HNL"))

runner = PythiaRunInterface(
    "outputs",
    new_particles=[9900012],
    pythia_settings=["PhaseSpace:pTHatMin = 20"],
    lifetimes={9900012: 1000.0},
    hard_cuts=[{
        "pdg_id": 9900012,
        "min_pt": 30.0,
        "max_eta": 2.5,
        "min_count": 1,
        "use_abs_id": True,
    }],
)

print(runner.check_runtime())
```

Generate a generic Pythia CMND file without a compiled binding:

```bash
setanubis-pythia-smoke --pid 42 --out pythia_smoke_outputs
```

Run the optional native runtime once the binding is compiled:

```bash
setanubis-pythia-smoke --run-pythia --no-hard-cut --events 5
```

## Repository layout

```text
setanubis/SetAnubis/core/
├── ModelCore/        # UFO/model-facing interface and parameter services
├── BranchingRatio/   # decay-width, BR and lifetime calculation layer
├── DataBase/         # event metadata, CAS bundles, card generation, UFO parsing
├── Pythia/           # CMND generation and optional C++/pybind11 runner
├── MadGraph/         # MadGraph card/running adapters
├── Geometry/         # ATLAS cavern and ANUBIS geometry models
└── Selection/        # HepMC/dataframe selection, cutflows, isolation, jets
```

## Documentation

- [Installation guide](INSTALL.md)
- [Pythia packaging guide](PYTHIA_PACKAGING.md)
- [Sphinx manual source](Docs/manual/source/index.rst)
- [Examples](setanubis/SetAnubis/examples/README.md)
- [Release process](RELEASE.md)

Build the local manual with:

```bash
python -m pip install -e ".[docs]"
sphinx-build -b html Docs/manual/source Docs/manual/build/html
```

## Dash interfaces

The GUI apps are optional and live inside the Python package tree:

- [`SetAnubis.HepMCGUI`](setanubis/SetAnubis/HepMCGUI/README.md): event and
  geometry visualisation.
- [`SetAnubis.SetAnubisDBDashboard`](setanubis/SetAnubis/SetAnubisDBDashboard/README.md):
  database and storage inspection.

Install GUI dependencies with:

```bash
python -m pip install "SetAnubis[app]"
```

## Development

```bash
git clone https://github.com/SET-ANUBIS/set-anubis.git
cd set-anubis
python -m pip install -e ".[dev,docs]"
python -m pytest -q setanubis/tests
python -m build
```

Native Pythia builds are covered by a separate workflow because Pythia8/HepMC3
are large external C++ dependencies.

## Citation

If SET-ANUBIS contributes to a study or publication, please cite the project and
the associated preprint placeholder:

```bibtex
@misc{setanubis2025,
  title  = {SET-ANUBIS: a modular pipeline for ANUBIS long-lived particle sensitivity studies},
  url    = {https://arxiv.org/abs/2512.14942},
  year   = {2025}
}
```

A structured citation is provided in [`CITATION.cff`](CITATION.cff).

## Community and governance

- [Contributing guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [Support policy](SUPPORT.md)
- [Changelog](CHANGELOG.md)

## License

SET-ANUBIS is distributed under the MIT License. See [`LICENSE`](LICENSE).
