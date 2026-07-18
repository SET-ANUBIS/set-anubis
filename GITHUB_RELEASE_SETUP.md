# GitHub, TestPyPI, PyPI and Zenodo release setup

This file records the release settings that cannot be fully expressed in the
version-controlled workflow YAML.

## 1. Repository rulesets

### `main`

Require pull requests, at least one approval, resolved conversations, no force
pushes, and the following status checks:

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

Replace the commented example in `.github/CODEOWNERS` with the actual GitHub
accounts or team before requiring CODEOWNER review. Do not invent a team name in
the repository configuration.

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

## 6. Zenodo: choose one first-release route

The repository contains `.zenodo.json`. Zenodo uses it instead of
`CITATION.cff` for GitHub release archiving. It records Théo Reymermier as
`ProjectLeader`, Paul Swallow as `ProjectManager`, and the remaining collaborators
as contributors.

### Recommended route: automatic GitHub release archiving

Use this route when the DOI does not need to be embedded in the repository before
the tag:

1. Sign in to Zenodo and connect the GitHub account with access to the repository.
2. Open the Zenodo GitHub integration, click **Sync now**, locate
   `SET-ANUBIS/set-anubis`, and enable it.
3. Create the `v1.0.0` GitHub Release through the release workflow.
4. Wait for Zenodo to archive the release and create the software record.
5. Verify creators, roles, contributors, licence, version and related article.
6. Add the resulting concept DOI badge to the README in a follow-up documentation
   commit and use the version DOI in release-specific citation material.

With the automatic route, the DOI is normally created after the GitHub Release,
not before the tag.

### Alternative route: reserve a DOI before the tag

Use this route only if the CPC manuscript or release files must contain the DOI in
advance:

1. Create a **New upload** in Zenodo and select resource type **Software**.
2. Complete the metadata but keep the record as a draft.
3. In the DOI field choose **Get a DOI now** to reserve one.
4. Add the reserved DOI to the manuscript and repository metadata.
5. After the release artifacts are final, upload one cleaned source ZIP, preview
   the record, and publish it.

Do not use the manual draft and automatic GitHub integration for the same
`v1.0.0` object unless you intentionally manage the duplicate-record risk. Pick
one archival route for the first software version.

## 7. Final release sequence

1. Merge the release pull request into `main` only after all required checks pass.
2. Verify `git status --short` is empty and metadata versions agree.
3. Create and push `v1.0.0`. A stable `X.Y.Z` tag starts the full TestPyPI-to-PyPI workflow automatically; pre-release tags stop after TestPyPI verification.
4. The workflow builds once, publishes to TestPyPI, downloads the TestPyPI wheel,
   compares its SHA-256 checksum, installs it in isolation and runs smoke tests.
5. Approve the `pypi` environment only after the TestPyPI verification job is
   green. A failed TestPyPI publish or verification prevents every downstream
   PyPI job from running.
6. Verify the PyPI files and GitHub Release attachments.
7. Complete the chosen Zenodo route and record the DOI.

```bash
git checkout main
git pull --ff-only
git status --short
git tag -s v1.0.0 -m "SET-ANUBIS 1.0.0"
git push origin v1.0.0
```
