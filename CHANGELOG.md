# Changelog

## 1.0.0 - 2026-07-20

First public stable release of SET-ANUBIS.

### Added

- Shared example runtime wrapper so every directly executed example displays the SET-ANUBIS banner once while remaining import-safe.
- Wheel-level smoke tests for example banners and JSON-only Pythia diagnostics.
- Public lower-case import facade: `from setanubis import ...`.
- Release documentation centred on the scientific workflow used in the paper:
  UFO/model input, branching ratios and lifetimes, MadGraph signal generation,
  event storage, ANUBIS geometry, selection cutflows and sensitivity inputs.
- ANUBIS detector context and references in README and Sphinx documentation.
- GitHub Actions workflows for CI, documentation, CodeQL, release publishing and
  optional Pythia-native builds.
- Optional Pythia8/HepMC3 native-extension build controlled by
  `SETANUBIS_BUILD_PYTHIA=1`.
- Resource helpers `asset_path()` and `ufo_path()` for checkout-independent and
  wheel-safe asset lookup.
- Release contract tests for all public exports, architecture interfaces, packaged
  examples and deterministic selection caches.
- Dependency-vulnerability auditing in the CI and release gates.
- Python 3.13 in the supported CI matrix and package classifiers.
- Additional unit coverage for scan conversion, geometry plotting and queries, MadGraph orchestration, HepMC event selection and documentation tooling.

### Changed

- Corrected the temporary `CITATION.cff` preferred citation to the actual title and author list of arXiv:2512.14942, while keeping the software creators separate.
- Pre-release tags now stop after TestPyPI validation; only stable semantic-version tags automatically continue to PyPI.
- Reworked the README and Sphinx manual in a scientific, workflow-oriented style aligned with the software article.
- Added project branding to the README, documentation and both Dash applications.
- Changed the project licence from MIT to GPL-3.0-or-later.
- Packaged the two optional Dash applications and added console entry points with bundled branding assets.
- Documented the protected-tag, Trusted Publisher and immutable-artifact release process.
- Added automated release-metadata and post-patch check scripts shared by local development, CI and the tag-driven publication workflow.
- Reserved and embedded the versioned Zenodo DOI `10.5281/zenodo.21462101` and added shared maintainer contact metadata.
- Public examples now use HNL-oriented MadGraph, branching-ratio and selection
  configurations rather than Pythia-first examples.
- Pythia documentation repositioned as an optional support layer.
- Selection documentation now describes the nominal cut order: decaying LLP,
  geometry, ATLAS-volume veto, ANUBIS station intersections, charged-track RPC
  hits, MET and isolation.
- `SetAnubisInterface` now uses packaged asset helpers instead of hard-coded
  `Assets/...` paths for the particle catalogue.

### Fixed

- Removed stale `SelectionEnginev2` wording from event-bundle metadata and comments.
- Removed an unused generated Sphinx theme stylesheet from the documentation source tree.
- Public API export target for `MadGraphCommandConfig`.
- Source-tree import shadowing around the `setanubis` facade.
- Pythia C++ compatibility with Pythia versions returning smart pointers from
  `particleDataEntryPtr`.
- Canonical `EventDatabaseManager` imports after the latest implementation replaced the versioned modules.
- Headless import of the MadGraph HepMC analyzer.
- MadGraph local-runner card placement (run and parameter cards were swapped).
- Selection bundle materialisation when no pre-transform list is supplied.
- SHA-256 cache fingerprints and removal of generated/macOS metadata from sources.
- Consolidated the 5.8 MB HNL branching-ratio table into one canonical packaged copy.
- Consolidated the selection stack under the non-versioned `SelectionEngine`, `ISelectionGeometry` and `SelectionGeometryAdapter` names.
- Updated selection examples to construct the current cavern geometry adapter and avoid the missing `default_decay_region` attribute.
- Restricted release-source validation to maintained and distributed code, excluding downloaded third-party toolchains and generated build trees.
- Fixed Pythia scan filename parsing and removed import-time root logger configuration.
- Fixed the generic geometry plotting adapter and `limit=0` handling in the event-database HepMC selector.
- Fixed the sampled decay-tree overlay in the HepMC dashboard when no event-level filter is active.
- Extended the dark dropdown theme to the React-Select classes used by current Dash releases in both GUI applications.

### Notes

- SET-ANUBIS is distributed under GPL-3.0-or-later. The CPC manuscript and any
  archived release metadata should use the same licence identifier.
