# SET-ANUBIS release checklist

This checklist describes the publication of SET-ANUBIS `1.0.0` to TestPyPI,
PyPI, GitHub Releases and the reserved Zenodo software record
[`10.5281/zenodo.21462101`](https://doi.org/10.5281/zenodo.21462101).

The release workflow is deliberately tag-driven. Pushing a matching stable tag
builds the distributions once, validates them on TestPyPI, pauses for approval,
promotes the same files to PyPI and creates the GitHub Release. Do not start a
second manual release workflow after pushing the tag.

## 1. Automated metadata checks

Run the fast checker after every release-related patch:

```bash
python scripts/check_release_metadata.py
python scripts/run_patch_checks.py
```

The metadata checker validates, among other invariants:

- the version in `pyproject.toml`, `SetAnubis/_version.py`, `CITATION.cff`,
  `.zenodo.json`, `CHANGELOG.md` and the Sphinx configuration;
- the release date and `GPL-3.0-or-later` licence declaration;
- the Zenodo DOI in `CITATION.cff`, the README and the PyPI project URLs;
- the shared maintainer contact, `CODEOWNERS` policy and release workflow;
- the absence of the retired `Assets/Test` directory and known DOI placeholders.

The full release-candidate gate is:

```bash
python scripts/run_patch_checks.py --full
# Offline fallback; CI still performs the dependency audit:
python scripts/run_patch_checks.py --full --skip-dependency-audit
```

This adds dependency and source audits, the complete test suite with coverage,
the R1--R5 reproducibility scenarios, strict documentation generation, package
construction and `twine` validation. The optional native Pythia/HepMC3 test
remains separate because it requires locally installed external libraries.

## 2. One-time GitHub configuration

### Maintainer team and CODEOWNERS

Create or verify the visible organization team `SET-ANUBIS/maintainers`, add the
release maintainers, and grant that team write or maintain access to the
repository. `.github/CODEOWNERS` assigns the full repository to that team.

After the team is valid, enable **Require review from Code Owners** in the
`main` branch ruleset. GitHub only recognizes a team as a code owner when the
team is visible and has repository write access.

### Required status checks

Keep the existing protected-branch checks and add the CI check named
`Release metadata consistency` after it has appeared in the first pull request.
Require pull requests, resolved conversations, no force pushes and the desired
review policy. The existing PR-only maintainer bypass can remain in place for
maintainer-authored release pull requests.

### Deployment environments

Create GitHub environments named exactly:

- `testpypi`: allow tags matching `v*`; no manual reviewer is required;
- `pypi`: allow tags matching `v*`; require the other release maintainer and
  enable prevention of self-review where practical;
- `github-pages`: allow documentation deployment from `main`.

### Trusted Publishers

Configure separate GitHub Actions Trusted Publishers on TestPyPI and PyPI:

| Field | TestPyPI | PyPI |
| --- | --- | --- |
| Project | `SetAnubis` | `SetAnubis` |
| Owner | `SET-ANUBIS` | `SET-ANUBIS` |
| Repository | `set-anubis` | `set-anubis` |
| Workflow | `release.yml` | `release.yml` |
| Environment | `testpypi` | `pypi` |

No long-lived package-index token is required.

### Reserved Zenodo DOI

Version `1.0.0` uses the manually reserved DOI
`10.5281/zenodo.21462101`. Keep the GitHub--Zenodo automatic archiving switch
disabled for this first release, otherwise the GitHub Release may create a
second Zenodo record.

Before tagging, keep the Zenodo record as a draft and verify its title,
creators, contributors, licence, version, release date and related HNL article.
The DOI will resolve publicly after the draft is published.

## 3. Release pull request

Create a release branch from the current protected `main` branch:

```bash
git switch main
git pull --ff-only
git switch -c release/v1.0.0
```

Apply the final metadata changes and run:

```bash
python scripts/run_patch_checks.py
python scripts/run_patch_checks.py --full
git status --short
```

Commit and push the release candidate:

```bash
git add -A
git commit -S -m "Prepare SET-ANUBIS 1.0.0 release"
git push -u origin release/v1.0.0
```

Open `release/v1.0.0 -> main`, wait for all required checks, obtain the required
review or use the configured PR-only maintainer bypass, and merge the pull
request without creating the release tag in the GitHub interface.

## 4. Final tag

After the pull request is merged:

```bash
git switch main
git pull --ff-only
git status --short
python scripts/check_release_metadata.py
VERSION=$(python scripts/check_release_metadata.py --print-version)
git tag -s "v${VERSION}" -m "SET-ANUBIS ${VERSION}"
git push origin "v${VERSION}"
```

An annotated tag can be used when tag signing is not configured, but a signed
tag is preferred. The tag must point to a commit contained in `origin/main`.

Do not invoke `gh workflow run release.yml` after this push. The tag push starts
the release workflow automatically.

## 5. Automated publication sequence

For a stable `X.Y.Z` tag, `.github/workflows/release.yml`:

1. validates the version, date, DOI, licence, contacts and tag using
   `scripts/check_release_metadata.py`;
2. verifies that the tagged commit belongs to `main`;
3. executes the reproducibility, test, security and documentation gates;
4. builds one wheel and one sdist;
5. creates a clean source ZIP, `RELEASE_METADATA.json` and `SHA256SUMS`;
6. uploads the wheel and sdist to TestPyPI;
7. downloads the TestPyPI wheel, verifies its checksum, installs it and runs
   smoke tests;
8. waits for approval of the protected `pypi` environment;
9. uploads the unchanged wheel and sdist to PyPI;
10. creates the GitHub Release and attaches the distributions, source ZIP,
    metadata report and checksums.

A pre-release tag such as `v1.0.1rc1` stops after successful TestPyPI
verification. Package indexes do not permit replacing an uploaded filename, so
never use the final version number for a rehearsal.

If a workflow job fails before publication, fix the underlying problem and move
to a new version or pre-release as appropriate. If a transient job fails after
an artefact was uploaded, use GitHub's **Re-run failed jobs** action rather than
starting a second independent workflow.

## 6. Zenodo publication

After the GitHub Release is complete, download
`set-anubis-1.0.0-source.zip` and `SHA256SUMS`. Verify the source archive against
the published checksum, then upload **only that clean source ZIP** to the existing
Zenodo software draft. Keeping one compressed source archive allows Zenodo to
forward the software record for Software Heritage archival. The wheel, source
distribution, checksum manifest and `RELEASE_METADATA.json` remain immutable
attachments of the GitHub Release.

Preview the Zenodo record and publish the draft. Then confirm that
<https://doi.org/10.5281/zenodo.21462101> resolves to the public software record.
Do not create a second automatic GitHub-derived Zenodo deposit for `v1.0.0`.

## 7. Post-publication verification

Test the public PyPI package outside the repository:

```bash
python -m venv /tmp/setanubis-release-check
. /tmp/setanubis-release-check/bin/activate
python -m pip install --upgrade pip
python -m pip install SetAnubis==1.0.0
python -c "import setanubis; print(setanubis.__version__)"
setanubis-pythia-smoke --out /tmp/setanubis-pythia-smoke
```

Also verify:

- TestPyPI and PyPI metadata, licence and README rendering;
- installation on Python 3.10 and 3.13;
- all GitHub Release attachments and SHA-256 values;
- GitHub Pages documentation;
- the public Zenodo record and citation export;
- the release entry in `CHANGELOG.md`.

## 8. CPC article follow-up

The CPC article is not required for `1.0.0`. Until the final CPC record is
public, `CITATION.cff` keeps the related ANUBIS proceedings article as its
`preferred-citation` and the software DOI identifies the released code.

When the CPC DOI and bibliographic record become available, update
`CITATION.cff`, the README and documentation. A repository-only documentation
commit is sufficient for the default branch, but PyPI metadata for an existing
file is immutable. Publish a metadata patch release, normally `1.0.1`, if the
CPC citation should also appear in the PyPI-rendered README and the archived
package metadata.
