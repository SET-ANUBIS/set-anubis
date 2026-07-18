# SET-ANUBIS release checklist

This checklist describes the publication of SET-ANUBIS 1.0.0 to TestPyPI, PyPI
and GitHub Releases.

## 1. Repository and metadata

Before tagging the release:

- merge the release candidate into `main`;
- confirm that CI, the dedicated R1--R5 reproducibility workflow, CodeQL, documentation and optional Pythia checks are green;
- confirm version `1.0.0` in `pyproject.toml`, `SetAnubis/_version.py`,
  `CHANGELOG.md` and `CITATION.cff`;
- confirm `GPL-3.0-or-later` in `LICENSE`, `pyproject.toml`, `CITATION.cff`, the
  README and the CPC manuscript;
- replace the temporary article reference when the CPC identifier is available;
- make sure the working tree contains no generated event folders, databases,
  external build trees, caches or macOS metadata.

## 2. Local release gates

```bash
python -m pip install -e ".[dev,docs,selection,madgraph]"
python -m compileall -q setanubis/SetAnubis setanubis/setanubis.py setanubis/__init__.py
setanubis-pythia-smoke --out .release-pythia-smoke
python -m ruff check .
python -m pip_audit
python -m bandit -q -lll -r setanubis/SetAnubis/core \
  -x setanubis/SetAnubis/core/UFOInterface/SM_NLO,setanubis/SetAnubis/core/BranchingRatio/app,setanubis/SetAnubis/core/DataBase/app,setanubis/SetAnubis/core/Geometry/app,setanubis/SetAnubis/core/MadGraph/app,setanubis/SetAnubis/core/Pythia/app,setanubis/SetAnubis/core/Selection/app
python -m pytest -q setanubis/tests \
  --cov=SetAnubis --cov-config=pyproject.toml \
  --cov-report=term-missing --cov-fail-under=58
python reproducibility/run_reproducibility.py --output-root .release-reproducibility
setanubis-docs --strict
rm -rf build dist *.egg-info setanubis/*.egg-info
python -m build
python -m twine check dist/*
sha256sum dist/*
```

Optional native Pythia/HepMC3 validation:

```bash
./External_Integration/install.sh HepMC3 Pythia
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
python -m pip install -e ".[pythia,dev]"
setanubis-pythia-check
setanubis-pythia-smoke --run-pythia --no-hard-cut --events 3
```

## 3. One-time GitHub, TestPyPI and PyPI setup

Create GitHub environments named exactly:

- `testpypi`
- `pypi`
- `github-pages`

Recommended protection:

- `pypi`: required maintainer approval, no self-review where practical, and
  deployment restricted to tags matching `v*`;
- `testpypi`: release workflow only; release-candidate branches or tags may be
  allowed;
- `github-pages`: deployments allowed from `main`.

Configure a separate Trusted Publisher on **TestPyPI** and **PyPI** with:

- owner: `SET-ANUBIS`
- repository: `set-anubis`
- workflow: `release.yml`
- environment: `testpypi` or `pypi`

No long-lived PyPI token is required by the workflow.

## 4. TestPyPI rehearsal

Use a release-candidate version, for example `1.0.0rc1`, for a rehearsal. Update
the package metadata to that version and push the matching tag `v1.0.0rc1`.
Pre-release tag pushes publish to TestPyPI and stop after verification; they do
not continue to PyPI. The manual workflow can also be run from that tag with
`target=testpypi`. Do not repeatedly upload the final `1.0.0` filename: package
indexes do not allow an uploaded distribution file to be replaced.

## 5. Final tagged release

After all checks are green on `main`:

```bash
git checkout main
git pull --ff-only
git status --short
git tag -s v1.0.0 -m "SET-ANUBIS 1.0.0"
git push origin v1.0.0
```

An annotated tag can be used when signing is not configured, but a signed tag is
preferred.

Run the workflow from the tag:

```bash
gh workflow run release.yml \
  --ref v1.0.0 \
  -f target=testpypi-and-pypi
```

The workflow:

1. verifies that `GITHUB_REF` is `refs/tags/v1.0.0` and matches the package
   version;
2. builds one wheel/sdist pair and records SHA-256 checksums;
3. uploads the files to TestPyPI;
4. downloads the TestPyPI wheel and compares its checksum with the retained
   build;
5. installs the wheel and runs smoke tests;
6. waits for approval of the `pypi` environment;
7. publishes the same files to PyPI;
8. creates the GitHub Release for the existing tag and attaches the same files.

## 6. Post-publication verification

```bash
python -m venv /tmp/setanubis-release-check
. /tmp/setanubis-release-check/bin/activate
python -m pip install --upgrade pip
python -m pip install SetAnubis==1.0.0
python -c "import setanubis; print(setanubis.__version__)"
setanubis-pythia-smoke --out /tmp/setanubis-pythia-smoke
```

Also verify:

- PyPI metadata, licence and README rendering;
- installation on Python 3.10 and 3.13;
- GitHub Release attachments and checksums;
- GitHub Pages documentation;
- the DOI/archive record when it is created.

## 7. Branch model after 1.0.0

Use `develop` as the integration branch and protect both `main` and `develop`.
Feature branches should merge into `develop`; release pull requests merge
`develop` into `main`. Hotfixes branch from `main` and are merged back into both
branches. Require CI and documentation checks before merging.
