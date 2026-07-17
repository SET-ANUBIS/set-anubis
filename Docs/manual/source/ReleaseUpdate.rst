Release notes and publication policy
====================================

SET-ANUBIS version ``1.0.0`` is the first release prepared for public PyPI/TestPyPI
publication.  The default distribution is a Python wheel containing the framework,
examples and lightweight assets.  Large external generators remain outside the
wheel and are configured explicitly by the user.

Release checklist
-----------------

* update ``pyproject.toml``, ``SetAnubis/_version.py``, ``CHANGELOG.md`` and
  ``CITATION.cff``;
* run the lint, dependency audit, high-severity security scan, 35 percent coverage gate and local CI commands from :doc:`CIAndDocs`;
* build and check the distribution with ``python -m build`` and
  ``python -m twine check dist/*``;
* run the complete ``reproducibility/`` validation package;
* build one immutable sdist/wheel set and record SHA-256 checksums;
* upload those artifacts to TestPyPI first;
* download the TestPyPI wheel, verify its SHA-256, then install and smoke-test it in a clean environment;
* approve promotion of the same artifacts to PyPI from the protected ``main`` branch;
* create the matching GitHub tag/release with those same artifacts.

Scientific provenance
---------------------

A release should preserve the exact cards, scan metadata, banners and selection
configuration used for examples or validation plots.  The database and
content-addressed storage layers are designed to make this information auditable
without forcing large generated HepMC samples into the Python package. The
lightweight CPC package and its expected outputs are documented in
:doc:`Reproducibility`.
