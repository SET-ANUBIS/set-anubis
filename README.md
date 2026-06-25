# SET-ANUBIS

[![CI](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/ci.yml/badge.svg)](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/ci.yml)
[![Docs](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/docs.yml/badge.svg)](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/docs.yml)
[![CodeQL](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/codeql.yml/badge.svg)](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/codeql.yml)
[![Release](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/release.yml/badge.svg)](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/SetAnubis.svg)](https://pypi.org/project/SetAnubis/)
[![Python](https://img.shields.io/pypi/pyversions/SetAnubis.svg)](https://pypi.org/project/SetAnubis/)
[![Wheel](https://img.shields.io/pypi/wheel/SetAnubis.svg)](https://pypi.org/project/SetAnubis/)
[![GitHub Release](https://img.shields.io/github/v/release/SET-ANUBIS/set-anubis?sort=semver)](https://github.com/SET-ANUBIS/set-anubis/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Citation](https://img.shields.io/badge/cite-arXiv%3A2512.14942-b31b1b.svg)](https://arxiv.org/abs/2512.14942)

**SET-ANUBIS** (*Simulation, accEptance and sensiTivity studies framework for
ANUBIS*) is a modular Python/C++ toolkit for long-lived-particle (LLP)
sensitivity studies for the proposed ANUBIS detector.

The package is organised around the physics workflow used in the paper:
UFO/model input, branching ratios and lifetimes, MadGraph campaign generation,
event storage, ATLAS cavern / ANUBIS geometry, selection cutflows and sensitivity
projections. Pythia support is available, but it is treated as an optional
generation backend rather than the centre of the public API.

<p align="center">
  <img src="Docs/assets/set-anubis-architecture.pdf" alt="SET-ANUBIS architecture" width="900">
</p>

## What SET-ANUBIS does

- **Model and UFO handling**: load UFO models, inspect particles and parameters,
  generate parameter cards and keep model metadata reproducible.
- **MadGraph-first generation workflow**: build job scripts, run cards, parameter
  cards, MadSpin cards and shower cards for scan campaigns that produce the
  standard `Events/run_*` layout.
- **Event database and provenance**: ingest generated samples, scan summaries,
  cards, banners and compact dataframe bundles into a SQLite + content-addressed
  storage model.
- **Geometry and selection**: apply ANUBIS/ATLAS-cavern truth-level acceptance,
  charged-track requirements, isolation, jet and lifetime-reweighting cutflows.
- **Branching ratios and lifetimes**: combine Python formulas, interpolation
  tables, UFO/MadGraph and MARTY-oriented strategies for widths and BRs.
- **Optional Pythia layer**: generate `.cmnd` files and, when explicitly built,
  run a native Pythia8/HepMC3 binding for standalone samples or showering tests.
- **Inspection tools**: optional Dash apps for HepMC event debugging and database
  campaign auditing.

## Installation

### Python package

```bash
python -m pip install SetAnubis
```

From a development checkout:

```bash
git clone https://github.com/SET-ANUBIS/set-anubis.git
cd set-anubis
python -m pip install -e ".[dev,docs]"
python -m pytest -q setanubis/tests
```

Useful extras:

```bash
python -m pip install "SetAnubis[selection]"  # pyhepmc/awkward/fastjet tools
python -m pip install "SetAnubis[madgraph]"   # Docker runner integration
python -m pip install "SetAnubis[app]"        # Dash inspection apps
python -m pip install "SetAnubis[docs]"       # local documentation build
```

### Optional Pythia/HepMC3 binding

The default wheel is Python-only. This is intentional: Pythia8 and HepMC3 are
large external C++ dependencies, so the native binding is built only when
requested explicitly.

```bash
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"
```

For a local checkout, the helper can first build local copies of HepMC3/Pythia8:

```bash
./External_Integration/install.sh HepMC3 Pythia
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
python -m pip install -e ".[pythia]"
setanubis-pythia-check
```

See [`PYTHIA_PACKAGING.md`](PYTHIA_PACKAGING.md) for the native-extension policy.

## Public API

Prefer the short import layer in scripts, notebooks and examples:

```python
from setanubis import (
    SetAnubisInterface,
    MadGraphCommandConfig,
    GeneralCardInterface,
    SelectionConfig,
    SelectionPipelineBuilder,
    DecayInterface,
    CalculationDecayStrategy,
    ufo_path,
)
```

The internal `SetAnubis.core...` paths remain importable for advanced users, but
new documentation should use `from setanubis import ...` where possible.

## Quick start: MadGraph campaign cards

This example builds the core text artefacts for a scan campaign without launching
MadGraph. The same strings can be executed through the Docker/local runner or
submitted to a batch system.

```python
from setanubis import SetAnubisInterface, MadGraphCommandConfig, GeneralCardInterface, ufo_path

model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
config = MadGraphCommandConfig(
    neo_set_anubis=model,
    model_in_madgraph="SM_HeavyN_CKM_AllMasses_LO",
    shower="py8",
    madspin="ON",
    cache=False,
)

cards = GeneralCardInterface(config)
cards.run_card_builder.set("nevents", 2000)
cards.madspin_builder.clear_decays()
cards.madspin_builder.add_decay("decay n1 > ell ell vv")

job = cards.jobscript_builder
job.add_process("generate p p > n1 ell # [QCD]")
job.set_output_launch("HNL_scan_demo")
job.configure_cards()
job.add_parameter_scan("MN1", "[0.5, 1.0, 2.0]")
job.add_parameter_scan("VeN1", "[1e-6, 1e-5]")

print(job.serialize())
print(cards.run_card_builder.serialize())
print(cards.madspin_builder.serialize())
```

Full examples live in [`setanubis/SetAnubis/examples/MadGraph`](setanubis/SetAnubis/examples/MadGraph).

## Quick start: selection cutflow

Selection starts from either a HepMC stream converted to dataframes or a compact
bundle stored by the database layer. The key user-facing objects are a geometry
adapter, a `SelectionConfig`, a `RunConfig` and a pipeline builder.

```python
from setanubis import (
    ATLASCavern,
    GeometrySelectionAdapter,
    SelectionGeometryAdapter,
    SelectionConfig,
    RunConfig,
    MinThresholds,
    MinDR,
    SelectionPipelineBuilder,
    SelectionManager,
    EventsBundleSource,
)

cavern = ATLASCavern()
geometry = SelectionGeometryAdapter(GeometrySelectionAdapter(cavern))

selection = SelectionConfig(
    geometry=geometry,
    minMET=30.0,
    minP=MinThresholds(LLP=0.1, chargedTrack=0.1, neutralTrack=0.1, jet=0.1),
    minPt=MinThresholds(LLP=0.0, chargedTrack=5.0, neutralTrack=5.0, jet=15.0),
    minDR=MinDR(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
    nStations=2,
    nIntersections=2,
    nTracks=1,
)

pipeline = (
    SelectionPipelineBuilder()
    .set_options(add_jets=True, compute_isolation=True, selection_mode="standard")
    .build()
)
source = EventsBundleSource.from_bundle_file("sample_bundle.pkl.gz")
result = SelectionManager(pipeline).run_many(
    named_sources=[("scan-point", source)],
    sel_cfg=selection,
    run_cfg=RunConfig(reweightLifetime=False, plotTrajectory=False),
)
print(result.cutflow_sum)
```

Full examples live in [`setanubis/SetAnubis/examples/Selection`](setanubis/SetAnubis/examples/Selection).

## Branching ratios and optional Pythia cards

The branching-ratio layer feeds both MadGraph/MadSpin studies and optional Pythia
`.cmnd` generation. Pythia is useful for standalone samples and cross-checks,
but release examples keep it in this supporting role.

```python
from setanubis import SetAnubisInterface, DecayInterface, CalculationDecayStrategy, ufo_path

model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
br = DecayInterface(model)
br.add_decays(
    [{"mother": 25, "daughters": [-13, 13]}],
    CalculationDecayStrategy.FILE_INTERPOLATION,
    {"file_path": "br_table.csv", "varying_params": ["mN1", "VeN1"], "format_type": "csv"},
)
print(br.get_brs(25))
```

Pythia CMND generation works without the native binding:

```bash
setanubis-pythia-smoke --pid 42 --out pythia_smoke_outputs
```

## Documentation

Build locally:

```bash
python -m pip install -e ".[docs]"
setanubis-docs --open
# equivalent:
sphinx-build -b html Docs/manual/source Docs/manual/build/html
```

The docs workflow always builds and uploads an HTML artifact. It deploys to
GitHub Pages only when Pages is enabled and either the repository variable
`DEPLOY_GITHUB_PAGES=true` is set for pushes to `main`, or the workflow is run
manually with `deploy_pages=true`.

## Repository layout

```text
setanubis/SetAnubis/core/
├── ModelCore/        # UFO/model-facing interface and parameter services
├── DataBase/         # card generation, event catalogue, CAS, campaign metadata
├── BranchingRatio/   # decay-width, BR and lifetime calculation strategies
├── MadGraph/         # MadGraph cards and execution adapters
├── Selection/        # HepMC/dataframe selection, cutflows, isolation, jets
├── Geometry/         # ATLAS cavern and ANUBIS geometry models
└── Pythia/           # optional CMND generation and native runtime binding
```

## Dash interfaces

The GUI apps are optional inspection tools, not required for production scans:

- [`SetAnubis.HepMCGUI`](setanubis/SetAnubis/HepMCGUI/README.md): HepMC event,
  track and geometry visualisation.
- [`SetAnubis.SetAnubisDBDashboard`](setanubis/SetAnubis/SetAnubisDBDashboard/README.md):
  event database and campaign-provenance dashboard.

Install GUI dependencies with:

```bash
python -m pip install "SetAnubis[app]"
```

## Release and citation

The package version is `1.0.0`. Release notes are tracked in
[`CHANGELOG.md`](CHANGELOG.md), and the release checklist is in
[`RELEASE.md`](RELEASE.md).

If SET-ANUBIS contributes to a study or publication, please cite the software and
the associated preprint placeholder:

```bibtex
@misc{setanubis2025,
  title  = {SET-ANUBIS: a modular pipeline for ANUBIS long-lived particle sensitivity studies},
  url    = {https://arxiv.org/abs/2512.14942},
  year   = {2025}
}
```

A machine-readable citation is provided in [`CITATION.cff`](CITATION.cff).

## Community and governance

- [Contributing guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [Support policy](SUPPORT.md)
- [Changelog](CHANGELOG.md)

## License

SET-ANUBIS is distributed under the MIT License. See [`LICENSE`](LICENSE).
