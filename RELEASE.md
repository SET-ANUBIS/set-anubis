# Release checklist

This checklist is intended for maintainers preparing a SET-ANUBIS release.

## 1. Pre-release checks

```bash
python -m pip install -e ".[dev,docs]"
python -m compileall -q setanubis/SetAnubis setanubis/setanubis.py setanubis/__init__.py
setanubis-pythia-smoke --out .release-pythia-smoke
python -m pytest -q setanubis/tests
setanubis-docs --strict
```

Optional native Pythia/HepMC3 check, from a checkout with local external builds:

```bash
./External_Integration/install.sh HepMC3 Pythia
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
python -m pip install -e ".[pythia,dev]"
setanubis-pythia-check
setanubis-pythia-smoke --run-pythia --no-hard-cut --events 3
```

## 2. Build distributions

```bash
rm -rf dist build *.egg-info
python -m build
python -m twine check dist/*
```

## 3. TestPyPI

Run the `Release` GitHub workflow manually with `repository=testpypi`. Then test
installation in a fresh environment.

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ SetAnubis
```

## 4. PyPI and GitHub release

Make sure the PyPI trusted publisher is configured for
`SET-ANUBIS/set-anubis`, workflow `.github/workflows/release.yml`, environment
`pypi`. Then create and push the matching tag:

```bash
git tag -a v1.0.0 -m "SetAnubis 1.0.0"
git push origin v1.0.0
```

The tag workflow builds the sdist/wheel, publishes to PyPI and attaches the
distributions to the GitHub release.

## 5. Documentation Pages

The `Docs` workflow always builds HTML and uploads an artifact. Pages deployment
requires repository Settings → Pages → Source = GitHub Actions. The public URL
will be shown in the `github-pages` deployment environment after the deploy job
succeeds.
