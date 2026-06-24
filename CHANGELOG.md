# Changelog

All notable changes to SET-ANUBIS will be documented in this file.

The project follows semantic versioning starting with the 1.0.0 release.

## [1.0.0] - 2026-06-24

### Added

- Release-ready Python packaging metadata for PyPI/TestPyPI.
- Optional Pythia/HepMC3 native-extension build controlled by
  `SETANUBIS_BUILD_PYTHIA`.
- Public short-import API through `import setanubis` and `import SetAnubis`.
- Packaged lightweight assets and resource helpers (`asset_path`, `ufo_path`).
- GitHub Actions workflows for CI, documentation, releases, CodeQL and optional
  Pythia runtime builds.
- Repository governance files: code of conduct, contributing guide, support
  policy, security policy, citation file and release checklist.
- Architecture figure and refreshed user/developer documentation.

### Changed

- Package version bumped to 1.0.0.
- Repository URLs now target `https://github.com/SET-ANUBIS/set-anubis`.
- Default installation is explicitly Python-only; native Pythia compilation is
  opt-in and documented.
- GUI README files now describe optional extras and package imports.

### Removed

- Stale Jenkins/Terraform/Ansible deployment placeholders.
- Duplicate zipped GUI snapshots from the Python package tree.
- macOS resource-fork files from UFO assets.
