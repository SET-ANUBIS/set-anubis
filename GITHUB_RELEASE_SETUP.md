# GitHub, TestPyPI, PyPI and Zenodo release setup

This file records the release settings that cannot be fully expressed in the
version-controlled workflow YAML.

## 1. Repository rulesets

### `main`

Require pull requests, at least one approval, resolved conversations, no force
pushes, and the following status checks:

- `Release metadata consistency`;
- all Python jobs from `CI`;
- `Packaging smoke test`;
- `Reproducibility / CPC R1-R5`;
- `Documentation / Build Sphinx documentation`;
- CodeQL.

Restrict direct pushes and tag creation to the release maintainers.

### `develop`

Use `develop` as the integration branch after the first release. Feature branches
merge into `develop`; release pull requests merge from `develop` into `main`.
Require CI, reproducibility and documentation checks before merging.

### Tags

Create a tag ruleset for `v*`. Restrict creation and deletion to release
maintainers. Use signed annotated release tags where practical.

## 2. CODEOWNERS

`.github/CODEOWNERS` assigns the repository to `@SET-ANUBIS/maintainers`.
Before enabling required CODEOWNER review:

1. create or verify the organization team `maintainers`;
2. add Théo Reymermier and Paul Swallow, or the current release maintainers;
3. make the team visible;
4. grant the team write or maintain access to `SET-ANUBIS/set-anubis`;
5. open the `main` ruleset and enable **Require review from Code Owners**.

GitHub does not accept a hidden team or a team without repository write access
as a CODEOWNER.

## 3. GitHub environments

Open **Repository → Settings → Environments → New environment**.

### `testpypi`

1. Create an environment named exactly `testpypi`.
2. Do not add an API token; Trusted Publishing uses OIDC.
3. Under deployment branches and tags, select **Selected branches and tags**.
4. Allow tag pattern `v*`. The final workflow is tag-driven and publishes to TestPyPI first.
5. A required reviewer is optional; TestPyPI can remain automatic.

### `pypi`

1. Create an environment named exactly `pypi`.
2. Add the other release maintainer as a required reviewer.
3. Enable **Prevent self-review** if Théo and Paul can approve each other's
   releases.
4. Optionally disable administrator bypass.
5. Restrict deployment to the tag pattern `v*` only.
6. Do not add a long-lived PyPI token.

The workflow already requires `environment: testpypi` / `environment: pypi` and
only gives `id-token: write` to the two publication jobs.

### `github-pages`

Allow branch `main`, select **GitHub Actions** under **Settings → Pages**, and
ensure that the environment protection rules permit `main` to deploy.

## 4. TestPyPI Trusted Publisher

TestPyPI and PyPI are separate services and require separate publisher records.
If `SetAnubis` does not yet exist on TestPyPI:

1. Sign in to <https://test.pypi.org/>.
2. Open the account **Publishing** page.
3. Add a **pending GitHub Actions publisher**.
4. Enter:

   | Field | Value |
   | --- | --- |
   | PyPI project name | `SetAnubis` |
   | GitHub owner | `SET-ANUBIS` |
   | Repository | `set-anubis` |
   | Workflow filename | `release.yml` |
   | Environment | `testpypi` |

5. Save the publisher.

A pending publisher creates the project on first successful upload; it does not
reserve the project name before that upload.

## 5. PyPI Trusted Publisher

Repeat the same procedure on <https://pypi.org/> with environment `pypi`:

| Field | Value |
| --- | --- |
| PyPI project name | `SetAnubis` |
| GitHub owner | `SET-ANUBIS` |
| Repository | `set-anubis` |
| Workflow filename | `release.yml` |
| Environment | `pypi` |

If the project already exists, open **Your projects → SetAnubis → Manage →
Publishing** and add the GitHub publisher there instead of creating a pending
publisher.

## 6. Zenodo reserved record for `v1.0.0`

The first release uses the manually reserved DOI
`10.5281/zenodo.21462101`. The repository contains `.zenodo.json` metadata with
Théo Reymermier as `ProjectLeader`, Paul Swallow as `ProjectManager` and the
remaining collaborators as contributors.

For this release:

1. keep the Zenodo GitHub automatic-archiving switch disabled for the repository;
2. retain the existing Zenodo draft and reserved DOI;
3. create the GitHub Release through the tag-driven workflow;
4. download the attached clean source ZIP and `SHA256SUMS`;
5. verify the source ZIP checksum and upload only that ZIP to the existing Zenodo
   software draft;
6. keep the wheel, sdist, checksum manifest and `RELEASE_METADATA.json` on the
   GitHub Release, then verify the Zenodo metadata and publish the draft.

The DOI is embedded in `CITATION.cff`, the README, PyPI project URLs and the
console banner. It becomes publicly resolvable when the Zenodo draft is
published. Do not enable automatic GitHub archiving for the same `v1.0.0`
release, because it may create a duplicate Zenodo record.

## 7. Final release sequence

1. Merge the release pull request into `main` only after all required checks pass.
2. Run `python scripts/run_patch_checks.py --full`, verify `git status --short` is empty, and confirm metadata versions agree.
3. Create and push `v1.0.0`. A stable `X.Y.Z` tag starts the full TestPyPI-to-PyPI workflow automatically; pre-release tags stop after TestPyPI verification.
4. The workflow builds once, publishes to TestPyPI, downloads the TestPyPI wheel,
   compares its SHA-256 checksum, installs it in isolation and runs smoke tests.
5. Approve the `pypi` environment only after the TestPyPI verification job is
   green. A failed TestPyPI publish or verification prevents every downstream
   PyPI job from running.
6. Verify the PyPI files and GitHub Release attachments.
7. Upload the attached clean source ZIP to the reserved Zenodo draft and publish DOI `10.5281/zenodo.21462101`.

```bash
git checkout main
git pull --ff-only
git status --short
git tag -s v1.0.0 -m "SET-ANUBIS 1.0.0"
git push origin v1.0.0
```
