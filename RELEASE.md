# Release checklist

This checklist is intended for maintainers preparing SET-ANUBIS 1.0.0.

## 1. Pre-release checks

```bash
python -m pip install -e ".[dev,docs]"
python -m compileall -q setanubis/SetAnubis setanubis/setanubis.py setanubis/__init__.py
setanubis-pythia-smoke --out .release-pythia-smoke
python -m ruff check .
python -m pip_audit
python -m bandit -q -lll -r setanubis/SetAnubis/core -x setanubis/SetAnubis/core/UFOInterface/SM_NLO,setanubis/SetAnubis/core/BranchingRatio/app,setanubis/SetAnubis/core/DataBase/app,setanubis/SetAnubis/core/Geometry/app,setanubis/SetAnubis/core/MadGraph/app,setanubis/SetAnubis/core/Pythia/app,setanubis/SetAnubis/core/Selection/app
python -m pytest -q setanubis/tests --cov=SetAnubis --cov-config=pyproject.toml --cov-fail-under=48
python reproducibility/run_all.py --output-dir .release-reproducibility
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

## 2. TestPyPI-only rehearsal

Run the `Release` GitHub workflow manually with `target=testpypi`. The workflow
builds and checks one sdist/wheel set, publishes it to TestPyPI, installs the
published wheel in a clean Python 3.12 environment, verifies that its SHA-256
matches the retained build artifact, and runs the public import and Pythia-CMND
smoke tests.

A TestPyPI-only run is best used with a version that will not later need to be
re-uploaded, because package indexes do not allow replacing an existing filename.

## 3. Final TestPyPI to PyPI promotion

For the final 1.0.0 release, run the workflow from the protected `main` branch with
`target=testpypi-and-pypi`. It performs this sequence in one workflow run:

1. build the sdist and wheel once;
2. record SHA-256 checksums and upload an immutable Actions artifact;
3. publish those files to TestPyPI;
4. download the TestPyPI wheel, compare its SHA-256 with the retained wheel, install it and run smoke tests;
5. wait for approval of the protected `pypi` environment;
6. verify the retained checksums and publish the same files to PyPI;
7. create tag `v1.0.0` and attach the same files to the GitHub release.

Configure Trusted Publishing for the environments `testpypi` and `pypi`. The
`pypi` environment should require maintainer approval so the TestPyPI install can
be inspected before promotion.

## 4. Clean-install verification

After publication:

```bash
python -m venv /tmp/setanubis-release-check
. /tmp/setanubis-release-check/bin/activate
python -m pip install --upgrade pip
python -m pip install SetAnubis==1.0.0
python -c "import setanubis; print(setanubis.__version__)"
setanubis-pythia-smoke --out /tmp/setanubis-pythia-smoke
```

## 5. Documentation Pages

The `Docs` workflow always builds HTML and uploads an artifact. Pages deployment
requires repository Settings → Pages → Source = GitHub Actions. The public URL
is shown in the `github-pages` deployment environment after deployment.
