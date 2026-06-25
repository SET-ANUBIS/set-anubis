# Changelog

## 1.0.0 - 2026-06-24

First public release candidate for SET-ANUBIS.

### Added

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

### Changed

- Public examples now use HNL-oriented MadGraph, branching-ratio and selection
  configurations rather than Pythia-first examples.
- Pythia documentation repositioned as an optional support layer.
- Selection documentation now describes the nominal cut order: decaying LLP,
  geometry, ATLAS-volume veto, ANUBIS station intersections, charged-track RPC
  hits, MET and isolation.
- `SetAnubisInterface` now uses packaged asset helpers instead of hard-coded
  `Assets/...` paths for the particle catalogue.

### Fixed

- Public API export target for `MadGraphCommandConfig`.
- Source-tree import shadowing around the `setanubis` facade.
- Pythia C++ compatibility with Pythia versions returning smart pointers from
  `particleDataEntryPtr`.

### Notes

- The repository license is MIT.  Older draft text in the paper mentioning GPLv2
  should be updated before article submission.
