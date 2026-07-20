Documentation and continuous integration
========================================

The public repository uses GitHub Actions to test the supported Python versions,
build the documentation, run security checks, validate the optional native
Pythia interface and publish release artefacts.

Local documentation build
-------------------------

.. code-block:: bash

   python -m pip install -e ".[docs]"
   setanubis-docs --strict

The equivalent direct Sphinx command is:

.. code-block:: bash

   sphinx-build -W --keep-going -b html Docs/manual/source Docs/manual/build/html

Warnings are treated as errors. Missing pages, images, API references or invalid
markup therefore fail the documentation workflow.

GitHub Pages
------------

The documentation workflow builds on ``main`` and ``develop`` and on pull
requests targeting either branch. Only a successful build from ``main`` is
deployed to GitHub Pages. Repository settings must use **GitHub Actions** as the
Pages source, and the ``github-pages`` environment must allow deployments from
``main``.

The expected public URL is:

.. code-block:: text

   https://set-anubis.github.io/set-anubis/

Local release-equivalent checks
-------------------------------

Install the maintainer dependencies once:

.. code-block:: bash

   python -m pip install -e ".[dev,docs,selection,madgraph]"

After each patch, run the fast consistency and contract checks:

.. code-block:: bash

   python scripts/run_patch_checks.py

Before a release pull request or tag, run the complete gate:

.. code-block:: bash

   python scripts/run_patch_checks.py --full

When PyPI is temporarily unreachable, maintainers can use
``--skip-dependency-audit`` locally; the GitHub release workflow still performs
the mandatory online audit.

The fast mode validates release metadata, compiles the maintained Python files,
runs the release lint and executes the metadata, branding and release-workflow
contract tests. The full mode adds dependency and source security audits, the
complete test suite with coverage, all R1--R5 reproducibility scenarios, the
Pythia command-generation smoke test, strict Sphinx documentation and package
construction with ``twine`` validation.

Release gates
-------------

The CI matrix covers Python 3.10, 3.11, 3.12 and 3.13. A dedicated
``Release metadata consistency`` job runs the repository-level metadata checker
on every pull request. The Python 3.12 job also runs the release lint,
dependency audit, high-severity source scan and coverage gate. A separate required ``Reproducibility / CPC R1-R5`` workflow runs the five
deterministic CPC scenarios and uploads their generated evidence. Generated UFO code, optional Dash
applications, examples and external toolchains are excluded from the coverage
metric; the current minimum is 58 percent over the maintained production
modules.

Contract tests additionally verify the public facade, public docstrings,
interface documentation, packaged example data, documentation assets, licence
metadata and release-source cleanliness. The packaging job builds an sdist and
wheel, checks their metadata and imports the installed wheel from outside the
source tree.
