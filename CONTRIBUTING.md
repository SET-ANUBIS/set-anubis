# Contributing to SET-ANUBIS

SET-ANUBIS is a scientific codebase. Reproducibility, explicit assumptions and
stable interfaces are therefore as important as adding new functionality.

## Development setup

```bash
git clone https://github.com/SET-ANUBIS/set-anubis.git
cd set-anubis
python -m pip install -e ".[dev,docs,selection,madgraph]"
python -m pytest -q setanubis/tests
```

## Branch model

After the 1.0.0 release, `develop` is the integration branch and `main` contains
release-ready code.

- Create feature and bug-fix branches from `develop`.
- Open ordinary pull requests against `develop`.
- Merge a tested release pull request from `develop` into `main`.
- Create hotfix branches from `main`, then merge the correction back into both
  `main` and `develop`.

Both protected branches should require the relevant CI and documentation checks.
Release tags are created from `main`.

## Contribution guidelines

- Use the public `setanubis` facade in examples and user-facing documentation.
- Keep domain logic independent from filesystems, subprocesses and external
  programs where possible; implement those concerns in adapters.
- State the physical convention, unit and parameter domain when adding a new
  calculation or selection requirement.
- Add tests for bug fixes and public API changes.
- Update the README, Sphinx manual and examples when user-visible behaviour
  changes.
- Mark tests requiring the compiled Pythia/HepMC3 extension with
  `pytest.mark.pythia`.
- Do not commit generated event campaigns, local databases, external tool
  builds, caches, scan folders or private samples.

## Native Pythia changes

The optional binding links against external Pythia8 and HepMC3 installations.
Run:

```bash
setanubis-pythia-check
```

before and after native-interface changes. If the extension cannot be compiled
locally, state that limitation in the pull request and ensure that the
Python-only command-file smoke tests remain green.

## Pull request checklist

- The scientific or technical motivation is stated clearly.
- Tests pass locally, or an external-runtime limitation is documented.
- Public interfaces, examples and documentation are consistent.
- New data files are minimal, have documented provenance and are redistributable.
- No generated or private artefacts are included.
- The contribution can be distributed under GPL-3.0-or-later.
