# Contributing to SET-ANUBIS

Thank you for considering a contribution. SET-ANUBIS is a scientific codebase,
so reproducibility and clear interfaces are as important as features.

## Development setup

```bash
git clone https://github.com/SET-ANUBIS/set-anubis.git
cd set-anubis
python -m pip install -e ".[dev,docs]"
python -m pytest -q setanubis/tests
```

## Contribution guidelines

- Prefer public imports from `setanubis` in examples and user-facing docs.
- Keep domain logic independent from file systems, subprocesses and external
  tools where possible; put integrations in adapters.
- Do not commit generated event outputs, local databases, external tool builds,
  scan folders or large private samples.
- Add tests for bug fixes and public API changes when practical.
- Update `README.md`, Sphinx docs or examples for user-facing behavior changes.
- Mark Pythia/HepMC3-dependent tests with `pytest.mark.pythia`.

## Native Pythia changes

The optional binding links against external Pythia8 and HepMC3. Use:

```bash
setanubis-pythia-check
```

before and after changes. If you cannot compile Pythia/HepMC3 locally, explain
that in the pull request and make sure the Python-only smoke tests still pass.

## Pull request checklist

- The PR has a clear summary and component label.
- Tests pass locally or the limitation is documented.
- Docs/examples are updated.
- No generated or heavy files are included.
