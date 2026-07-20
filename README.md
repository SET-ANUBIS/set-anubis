# SET-ANUBIS

<p align="center">
  <img src="https://raw.githubusercontent.com/SET-ANUBIS/set-anubis/main/Docs/assets/set-anubis-logo.png" alt="SET-ANUBIS logo" width="220">
</p>

<p align="center"><strong>Simulation, accEptance and sensiTivity studies framework for ANUBIS</strong></p>

[![CI](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/ci.yml/badge.svg)](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/ci.yml)
[![Docs](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/docs.yml/badge.svg)](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/docs.yml)
[![CodeQL](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/codeql.yml/badge.svg)](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/codeql.yml)
[![Release](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/release.yml/badge.svg)](https://github.com/SET-ANUBIS/set-anubis/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/SetAnubis.svg)](https://pypi.org/project/SetAnubis/)
[![Python](https://img.shields.io/pypi/pyversions/SetAnubis.svg)](https://pypi.org/project/SetAnubis/)
[![GitHub Release](https://img.shields.io/github/v/release/SET-ANUBIS/set-anubis?sort=semver)](https://github.com/SET-ANUBIS/set-anubis/releases)
[![License: GPL v3+](https://img.shields.io/badge/License-GPL%20v3%2B-blue.svg)](LICENSE)
[![Paper](https://img.shields.io/badge/arXiv-2606.26862-b31b1b.svg)](https://arxiv.org/abs/2606.26862)
[![Citation](https://img.shields.io/badge/citation-CITATION.cff-b31b1b.svg)](CITATION.cff)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21462101.svg)](https://doi.org/10.5281/zenodo.21462101)

**SET-ANUBIS** is a modular framework for studying the sensitivity of the proposed **ANUBIS** detector to scenarios containing long-lived particles (LLPs). It provides a common analysis chain from the definition of a beyond-the-Standard-Model (BSM) spectrum to the calculation of decay properties, event generation, event ingestion, detector-geometry acceptance and truth-level event selection.

The framework was developed to reduce the model-specific code normally required for LLP sensitivity studies. A model supplied in Universal Feynman Output (UFO) format can be connected to several calculation and generation strategies, while the downstream geometry and selection stages remain common. This makes it possible to compare models using the same detector description, selection logic and provenance machinery.

## Scientific scope

ANUBIS is a proposed transverse LLP detector at LHC Point 1. The detector concept uses resistive-plate-chamber tracking stations in the ATLAS cavern and service-shaft infrastructure. It is intended to provide sensitivity to neutral LLPs that escape the main ATLAS detector before decaying into charged final states in the surrounding cavern volume.

<p align="center">
  <img src="https://raw.githubusercontent.com/SET-ANUBIS/set-anubis/main/Docs/assets/anubis-ceiling-concept.png" alt="ANUBIS detector concept in the ATLAS cavern" width="620">
</p>

<p align="center"><em>ANUBIS ceiling-detector concept and LHC Point-1 geometry, reproduced from the ANUBIS proposal (arXiv:1909.13022) under CC BY-NC-ND 4.0. The PDF page was converted to PNG without altering its content.</em></p>

SET-ANUBIS addresses three connected parts of an ANUBIS sensitivity study:

1. **Signal-sample preparation.** Model parameters and particle properties are read from UFO inputs; decay widths, branching ratios and lifetimes are supplied through interchangeable calculation strategies; MadGraph or optional Pythia workflows are then prepared for event generation.
2. **Geometric acceptance and event selection.** HepMC events are converted into analysis objects and propagated through a model of the ATLAS cavern and ANUBIS tracking stations. The selection applies decay-volume, station-intersection, tracking, missing-transverse-momentum and isolation requirements.
3. **Sensitivity inputs and provenance.** Acceptances can be combined with luminosities, production cross sections, branching fractions and signal efficiencies. Cards, scan metadata, compact event bundles and derived artefacts can be stored with content-based identifiers for later inspection or reproduction.

## Software organisation

The code is organised using ports and adapters. Each physics domain exposes a small interface, while file formats, databases, external programs and visualisation tools are implemented as adapters. This separation keeps the physics logic testable and allows individual backends to be replaced without rewriting the complete workflow.

<p align="center">
  <img src="https://raw.githubusercontent.com/SET-ANUBIS/set-anubis/main/Docs/assets/set-anubis-architecture.jpg" alt="SET-ANUBIS software architecture" width="900">
</p>

The principal subsystems are:

- **Model core and UFO interface** — expose scan parameters, particle content and packaged model resources.
- **Decay-property layer** — evaluate or prepare partial widths, total widths, branching ratios and lifetimes using Python functions, interpolation tables, UFO information, MadGraph or MARTY-oriented workflows.
- **MadGraph layer** — construct process commands, run cards, parameter cards, MadSpin cards and shower configuration for scan points.
- **Pythia layer** — prepare `.cmnd` files and optionally build a native Pythia8/HepMC3 interface for dedicated studies.
- **Geometry and selection** — convert HepMC events into dataframe bundles, build prompt jets and isolation variables, evaluate the ANUBIS geometry and apply the analysis cutflow.
- **Database and content-addressed storage** — retain scan metadata and compact, selection-ready event bundles while avoiding unnecessary duplication of large generator outputs.
- **Dash applications** — inspect HepMC events in the cavern geometry and audit the database, stored artefacts and bundle sizes.

## Installation

The Python distribution is named `SetAnubis`:

```bash
python -m pip install SetAnubis
```

For a development checkout:

```bash
git clone https://github.com/SET-ANUBIS/set-anubis.git
cd set-anubis
python -m pip install -e ".[dev,docs,selection,madgraph]"
python -m pytest -q setanubis/tests
```

Optional feature groups are available through extras:

```bash
python -m pip install "SetAnubis[selection]"  # HepMC ingestion and selection helpers
python -m pip install "SetAnubis[madgraph]"   # MadGraph/Docker helpers
python -m pip install "SetAnubis[app]"        # Dash applications
python -m pip install "SetAnubis[docs]"       # local Sphinx documentation
```

### Optional Pythia8/HepMC3 extension

The standard wheel is Python-only. The native interface is built only when it is explicitly requested and the external installations are supplied:

```bash
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"
```

For a local checkout, the external helper can build HepMC3 and Pythia8 before the editable installation:

```bash
./External_Integration/install.sh HepMC3 Pythia
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
python -m pip install -e ".[pythia]"
setanubis-pythia-check
```

The native-build policy and supported environment variables are described in [`PYTHIA_PACKAGING.md`](PYTHIA_PACKAGING.md).

## Public Python interface

The recommended import layer is the lower-case module `setanubis`:

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

Internal modules under `SetAnubis.core` remain available for advanced development, but analysis scripts and public examples should use the stable facade whenever possible.

## Worked workflows

### MadGraph card preparation

The following example prepares an HNL scan without launching MadGraph:

```python
from setanubis import (
    SetAnubisInterface,
    MadGraphCommandConfig,
    GeneralCardInterface,
    ufo_path,
)

model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
config = MadGraphCommandConfig(
    neo_set_anubis=model,
    model_in_madgraph="UFO_HNL",
    shower="py8",
    madspin="ON",
    cache=False,
)

cards = GeneralCardInterface(config)
cards.run_card_builder.set("nevents", 2000)
cards.run_card_builder.set("ebeam1", 6800)
cards.run_card_builder.set("ebeam2", 6800)

cards.madspin_builder.clear_decays()
cards.madspin_builder.add_decay("decay n1 > ell ell vv")

job = cards.jobscript_builder
job.add_process("generate p p > n1 ell # [QCD]")
job.set_output_launch("HNL_ANUBIS_scan")
job.configure_cards()
job.add_parameter_scan("MN1", "[0.5, 1.0, 2.0]")
job.add_parameter_scan("VeN1", "[1e-6, 1e-5]")

print(job.serialize())
```

Additional examples are available in [`setanubis/SetAnubis/examples/MadGraph`](setanubis/SetAnubis/examples/MadGraph).

### Branching ratios, decay widths and lifetimes

The branching-ratio examples demonstrate each supported preparation path: explicit values, trusted Python calculators, interpolation tables, UFO-derived functions, MadGraph preparation and MARTY source preparation.

```bash
python setanubis/SetAnubis/examples/BranchingRatio/dev_examples/example_manual_values_and_lifetime.py
python setanubis/SetAnubis/examples/BranchingRatio/dev_examples/example_file_interpolation.py
python setanubis/SetAnubis/examples/BranchingRatio/dev_examples/example_madgraph_preparation.py --output-dir prepared_widths
python setanubis/SetAnubis/examples/BranchingRatio/dev_examples/example_marty_preparation.py --output prepared_marty/z_to_ddbar.cpp
```

The preparation examples do not run MadGraph, Docker, a compiler or MARTY. Python calculators and UFO models are executable inputs and should only be loaded from trusted sources.

### Geometry-aware selection and cutflow tracing

The nominal cutflow first identifies LLP decays in the relevant cavern or shaft volume, rejects vertices inside ATLAS, evaluates the ANUBIS station and track intersections, and finally applies missing-transverse-momentum and isolation requirements.

```python
from setanubis import (
    ATLASCavernGeometry,
    ATLASCavernGeometryConfig,
    SelectionGeometryAdapter,
    SelectionConfig,
    RunConfig,
    MinThresholds,
    MinDR,
    SelectionPipelineBuilder,
    EventsBundleSource,
)

geometry = SelectionGeometryAdapter(
    ATLASCavernGeometry.create(
        ATLASCavernGeometryConfig(mode="ceiling", origin="IP", use_cache=False)
    )
)

selection = SelectionConfig(
    geometry=geometry,
    minMET=30.0,
    minP=MinThresholds(LLP=0.1, chargedTrack=0.1, neutralTrack=0.1, jet=0.1),
    minPt=MinThresholds(LLP=0.0, chargedTrack=5.0, neutralTrack=5.0, jet=15.0),
    minDR=MinDR(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
    nStations=2,
    nIntersections=2,
    nTracks=2,
)

pipeline = (
    SelectionPipelineBuilder()
    .set_options(add_jets=True, compute_isolation=True, selection_mode="standard")
    .build()
)
source = EventsBundleSource.from_bundle_file("sample_bundle.pkl.gz")
result = pipeline.run(source, selection, RunConfig(capture_intermediate=True))

trace = result["trace"]
print(trace.candidate_summary)
print(trace.event_summary)
trace.write_report("selection_trace_output")
```

The repository includes a compact seven-event HNL sample selected from a 4,000-event corpus. It contains representative events that fail at `InCavern`, `NotInATLAS`, `Geometry`, `Tracker`, `MET` and `IsoJets`, together with one event that reaches the final selection. The aligned HepMC, compressed CSV, trusted compressed-pickle bundle and provenance manifest occupy less than 1 MB.

```bash
python setanubis/SetAnubis/examples/Selection/example_real_selection_trace_report.py \
  --output-dir selection_trace_output
```

> **Security note:** loading a pickle can execute arbitrary Python code. Only load bundles produced by a trusted SET-ANUBIS workflow or obtained from a verified source. See [`SECURITY.md`](SECURITY.md).

## Console banners

The public API can display a compact SET-ANUBIS banner once per Python process.
The default `auto` mode only prints in an interactive terminal, so redirected
logs, notebooks and CI jobs remain quiet unless the banner is explicitly
requested.

```bash
export SETANUBIS_BANNER=always  # force the SET-ANUBIS banner
export SETANUBIS_BANNER=never   # disable it
```

```python
from setanubis import show_banner

show_banner(force=True)
```

The SET-ANUBIS banner identifies the software version and developers, reports
whether the optional compiled Pythia binding is available in the current Python
environment, and reminds users to cite the current ANUBIS proceedings
contribution together with the versioned Zenodo software record
[`10.5281/zenodo.21462101`](https://doi.org/10.5281/zenodo.21462101). The
`SETANUBIS_ZENODO_DOI` environment variable remains available as an explicit
override for development builds and later releases.

FastJet prints its own citation banner the first time a clustering sequence is
created. SET-ANUBIS suppresses that console output by default so that selection
jobs, notebooks and CI logs remain concise. Users can restore it explicitly:

```bash
export SETANUBIS_FASTJET_BANNER=1
```

or in Python:

```python
from setanubis import JetClustering, JetClusteringConfig

clustering = JetClustering(JetClusteringConfig(show_banner=True))
```

Suppressing the FastJet console banner does not alter the clustering algorithm
and does not remove the requirement to cite FastJet in scientific work.

## Reproducibility

The [`reproducibility/`](reproducibility/) directory contains five deterministic CPC scenarios, labelled **R1–R5**. Each scenario has a documented `input/`, a generated `output/` directory excluded from Git, a version-controlled `expected_output/`, and an independently executable `run.py`.

- **R1** checks the public model interface and bundled HNL UFO.
- **R2** reproduces reference partial widths, total width and branching ratios.
- **R3** generates a deterministic Pythia command card without running Pythia.
- **R4** generates MadGraph, run, parameter, shower and MadSpin cards without running MadGraph or Docker.
- **R5** rebuilds the seven-event sample directly from the packaged HepMC2 input and reproduces the geometry-aware selection cutflow and trace report.

```bash
python -m pip install -e ".[dev,selection]"
python reproducibility/run_reproducibility.py \
  --output-root reproducibility_outputs
```

A successful run creates `reproducibility_outputs/VALIDATED`. The generated summaries are compared with the corresponding `expected_output/summary.json` files. The dedicated **Reproducibility / CPC R1-R5** GitHub workflow is intended to be a required status check before merging or releasing.

## Interactive applications

The optional Dash applications are specialised scientific inspection tools rather than generic dashboards:

- **HepMC selection explorer** — starts from the packaged CPC R5 HNL sample, reproduces the ordered selection cutflow, identifies the first failed stage for each event, and overlays LLP vertices and decay topologies on the ATLAS-cavern/ANUBIS geometry.
- **Campaign database inspector** — starts from an internal SQLite/CAS demonstration workspace and audits generator provenance, scan metadata, retained artifacts and selection-ready DataFrame bundles.

Install and launch them with:

```bash
python -m pip install "SetAnubis[app,selection]"
setanubis-hepmc-explorer --host 127.0.0.1 --port 8050
setanubis-db-dashboard --host 127.0.0.1 --port 8051
```

Both applications have usable packaged defaults. Local HepMC files or campaign databases can be selected from their sidebars; explicit database paths remain available through `--db`, `--storage` and `--events-root`. The version-controlled selection and geometry APIs, not an interactive screenshot, remain the source of truth for published results.

## Documentation and validation

The Sphinx manual is hosted at <https://set-anubis.github.io/set-anubis/>. A strict local build can be run with:

```bash
python -m pip install -e ".[docs]"
setanubis-docs --strict
```

The release gate includes the Python 3.10–3.13 test matrix, public-API contract tests, static checks, dependency and source security scans, deterministic reproducibility examples, documentation warnings as errors, package construction and clean-wheel installation.

Maintainers can run the fast post-patch checks and the complete release-candidate gate with:

```bash
python scripts/run_patch_checks.py
python scripts/run_patch_checks.py --full
```

The underlying `scripts/check_release_metadata.py` command verifies that the package version, release date, DOI, licence, contacts, changelog, Sphinx metadata and release workflow remain coherent. Maintainer-side GitHub environment, branch-protection and Trusted Publisher settings are documented in [`GITHUB_RELEASE_SETUP.md`](GITHUB_RELEASE_SETUP.md).

## Citation and archival

Citation metadata for the software is provided in [`CITATION.cff`](CITATION.cff). Until the dedicated *Computer Physics Communications* software article is available, its `preferred-citation` points to the related ANUBIS proceedings contribution, [*ANUBIS: Projected Sensitivities and Initial Results from the proANUBIS demonstrator with Run 3 LHC data*](https://arxiv.org/abs/2512.14942). Replace that temporary preferred citation with the final CPC record when it becomes public.

The ANUBIS HNL sensitivity study obtained with SET-ANUBIS is available as [*Projected sensitivity of the ANUBIS detector to heavy neutral leptons*](https://arxiv.org/abs/2606.26862). Users should cite the software record and the physics article(s) relevant to the analysis being reproduced.

Version `1.0.0` is archived under the reserved Zenodo DOI [`10.5281/zenodo.21462101`](https://doi.org/10.5281/zenodo.21462101). The repository also contains [`.zenodo.json`](.zenodo.json) metadata for the manual software deposit. Because the DOI was reserved in a Zenodo draft before tagging, the GitHub--Zenodo automatic archiving integration must remain disabled for this first release to avoid creating a duplicate record. Upload the clean `set-anubis-1.0.0-source.zip` attached to the GitHub Release to that draft before publication, and verify its SHA-256 value against `SHA256SUMS`. The wheel, source distribution, checksums and validated release-metadata report remain available as immutable GitHub Release assets.

## Project roles and contributors

- **Théo Reymermier** — Project Leader and Lead Developer
- **Paul Swallow** — Project Manager and Developer
- **Contributors** — Sofie Erner, Anna Mullin, Toby Satterthwaite and Oleg Brandt

The software creator and contributor roles are recorded in [`.zenodo.json`](.zenodo.json); the complete acknowledgement list is maintained in [`AUTHORS.md`](AUTHORS.md).

## License

SET-ANUBIS is free software distributed under the **GNU General Public License, version 3 or any later version** (`GPL-3.0-or-later`). See [`LICENSE`](LICENSE). Files originating from external projects remain subject to their respective upstream terms where indicated.
