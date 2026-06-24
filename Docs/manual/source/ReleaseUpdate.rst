Release process
===============

The release process is documented in ``RELEASE.md`` at the repository root.

Summary
-------

1. Update version metadata in ``pyproject.toml``, ``SetAnubis/_version.py`` and
   ``CITATION.cff``.
2. Update ``CHANGELOG.md``.
3. Run tests and package checks locally.
4. Publish to TestPyPI with the GitHub ``Release`` workflow.
5. Push a version tag such as ``v1.0.0`` to publish to PyPI.
