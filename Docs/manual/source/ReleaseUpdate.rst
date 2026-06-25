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
* run the local CI commands from :doc:`CIAndDocs`;
* build and check the distribution with ``python -m build`` and
  ``python -m twine check dist/*``;
* upload to TestPyPI first;
* test installation from TestPyPI in a clean environment;
* publish a GitHub release/tag and then publish to PyPI.

Scientific provenance
---------------------

A release should preserve the exact cards, scan metadata, banners and selection
configuration used for examples or validation plots.  The database and
content-addressed storage layers are designed to make this information auditable
without forcing large generated HepMC samples into the Python package.
