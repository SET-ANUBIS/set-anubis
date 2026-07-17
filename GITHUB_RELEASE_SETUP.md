# GitHub, TestPyPI and PyPI release setup

This file records the repository settings that cannot be expressed completely in
version-controlled workflow YAML.

## 1. Branches and rulesets

### `main`

Recommended protections:

- require a pull request before merging;
- require at least one approval;
- dismiss stale approvals after new commits;
- require conversation resolution;
- require the CI matrix, packaging, documentation and CodeQL checks;
- block force pushes and branch deletion;
- restrict direct pushes to release maintainers.

### `develop`

Use `develop` as the integration branch after 1.0.0. Require CI and documentation
checks before merging. Feature branches target `develop`; release pull requests
target `main`.

### Tags

Create a tag ruleset for `v*` that restricts tag creation and deletion to release
maintainers. Signed annotated tags are preferred.

## 2. CODEOWNERS

`.github/CODEOWNERS` contains a commented example because the repository-specific
maintainer team is not known to the package. Replace it with a valid GitHub user
or team before enabling required code-owner reviews, for example:

```text
* @SET-ANUBIS/maintainers
```

## 3. GitHub environments

Create these environments under **Settings → Environments**.

### `testpypi`

- allow the `Release` workflow;
- optionally restrict deployment to release-candidate branches or tags;
- no package token is needed when Trusted Publishing is configured.

### `pypi`

- require a maintainer approval;
- prevent self-review where practical;
- restrict deployment to tags matching `v*`;
- do not store a long-lived PyPI API token.

### `github-pages`

- allow deployment from `main`;
- if the environment currently rejects `main`, update its deployment-branch rule;
- under **Settings → Pages**, select **GitHub Actions** as the source.

## 4. Trusted Publishers

Configure publishers independently on TestPyPI and PyPI.

| Field | Value |
| --- | --- |
| Owner | `SET-ANUBIS` |
| Repository | `set-anubis` |
| Workflow filename | `release.yml` |
| Environment | `testpypi` or `pypi` |

For a project that does not yet exist on an index, create a pending publisher.
A pending publisher does not reserve the project name until the first successful
publication.

## 5. Final release command

After tagging the final commit:

```bash
gh workflow run release.yml \
  --ref v1.0.0 \
  -f target=testpypi-and-pypi
```

The workflow publishes to TestPyPI, verifies the downloaded wheel and checksum,
waits for approval of the `pypi` environment, promotes the same artefacts to PyPI
and creates the GitHub Release for the existing tag.

## 6. Zenodo release archiving

Before creating the public `v1.0.0` release, sign in to Zenodo with the GitHub account that can access the repository and enable `SET-ANUBIS/set-anubis` under the GitHub integration settings. The repository ships `.zenodo.json`, so the first GitHub release can populate the software metadata automatically. Zenodo uses `.zenodo.json` in preference to `CITATION.cff` when both are present, so verify that the two files agree before tagging.

After Zenodo creates the deposit:

1. verify the title, creators, GPL-3.0-or-later licence and related publication;
2. copy the **concept DOI** into the README badge and `CITATION.cff`;
3. keep the version DOI in the GitHub release notes and release checklist;
4. separately verify that the wheel, sdist and checksum file attached to the GitHub Release match the artifacts validated by the release workflow.

The DOI must not be guessed in advance.
