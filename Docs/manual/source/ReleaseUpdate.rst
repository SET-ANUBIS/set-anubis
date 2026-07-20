Release and publication policy
==============================

Version ``1.0.0`` is the first public SET-ANUBIS release. The release consists of
one source distribution and one Python wheel, built once and promoted unchanged
from TestPyPI to PyPI. External generators and locally compiled libraries are not
included in the wheel.

Pre-release requirements
------------------------

Before creating the release tag:

* run ``python scripts/check_release_metadata.py`` to validate the version,
  release date, DOI, licence, contacts, changelog, Sphinx metadata and workflow;
* confirm that the licence expression is ``GPL-3.0-or-later`` and that the CPC
  manuscript uses the same wording;
* run the local checks described in :doc:`CIAndDocs`;
* build the distributions with ``python -m build`` and validate them with
  ``python -m twine check dist/*``;
* run and validate all five ``reproducibility/`` scenarios (R1--R5);
* inspect the wheel and sdist for generated files, local databases, external
  build trees and private samples;
* merge the release candidate into the protected ``main`` branch.

Tag and immutable artefacts
---------------------------

The final workflow must be started from a tag matching the package version. For
version ``1.0.0`` the tag is ``v1.0.0``. The workflow checks that the selected
Git ref and package metadata agree, builds the distributions once and records
SHA-256 checksums.

A TestPyPI-only rehearsal should use a release-candidate version such as
``1.0.0rc1`` and the matching tag ``v1.0.0rc1``. Pre-release tag pushes stop
after TestPyPI verification; only a stable ``X.Y.Z`` tag automatically continues
to PyPI. Package indexes do not permit an existing distribution filename to be
replaced, so the final ``1.0.0`` files should be uploaded only by the final
promotion workflow.

Trusted Publishing
------------------

PyPI and TestPyPI require separate Trusted Publisher configurations. Each
publisher should identify:

* GitHub owner ``SET-ANUBIS``;
* repository ``set-anubis``;
* workflow ``release.yml``;
* environment ``testpypi`` or ``pypi``.

The ``pypi`` GitHub environment should require a maintainer approval and allow
only tags matching ``v*``. The ``testpypi`` environment can be less restrictive,
but it should still limit deployment to the release workflow.

Zenodo archival
----------------

The repository contains ``.zenodo.json`` metadata with Théo Reymermier as
``ProjectLeader``, Paul Swallow as ``ProjectManager`` and the remaining
collaborators as contributors. Zenodo uses this file instead of ``CITATION.cff``
when a GitHub release is archived.

The first release uses a manual Zenodo draft with reserved version DOI
``10.5281/zenodo.21462101``. The DOI is embedded in the repository metadata
before tagging. The automatic GitHub--Zenodo archiving switch must remain
disabled for ``v1.0.0`` to avoid creating a duplicate record.

After the GitHub Release is complete, upload its clean source ZIP, wheel, source
distribution, ``SHA256SUMS`` and ``RELEASE_METADATA.json`` to the existing
Zenodo draft, verify the metadata and checksums, and publish that draft.

Final promotion sequence
------------------------

The final workflow performs the following steps:

1. check out the tagged commit, validate it with
   ``scripts/check_release_metadata.py`` and execute all release gates;
2. build the wheel and sdist once, create a clean source ZIP and record all
   checksums and release metadata;
3. publish those files to TestPyPI;
4. download the TestPyPI wheel, compare its SHA-256 digest with the retained
   artefact, install it and run smoke tests;
5. pause at the protected ``pypi`` environment for manual approval;
6. publish the same files to PyPI;
7. create the GitHub Release for the existing tag and attach the distributions,
   clean source ZIP, metadata report and checksum file.

Scientific provenance
---------------------

A scientific release should preserve the exact cards, model parameters, random
seeds, selection configuration and software environment needed to interpret its
validation outputs. The database and content-addressed store make these records
auditable without forcing full generator campaigns into the Python package. The
small deterministic validation set is described in :doc:`Reproducibility`.
