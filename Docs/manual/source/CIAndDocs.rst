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

.. code-block:: bash

   python -m pip install -e ".[dev,docs,selection,madgraph]"
   python -m compileall -q setanubis/SetAnubis setanubis/setanubis.py setanubis/__init__.py
   setanubis-pythia-smoke --out .ci-pythia-smoke
   python -m ruff check .
   python -m pip_audit
   python -m bandit -q -lll -r setanubis/SetAnubis/core \
      -x setanubis/SetAnubis/core/UFOInterface/SM_NLO,setanubis/SetAnubis/core/BranchingRatio/app,setanubis/SetAnubis/core/DataBase/app,setanubis/SetAnubis/core/Geometry/app,setanubis/SetAnubis/core/MadGraph/app,setanubis/SetAnubis/core/Pythia/app,setanubis/SetAnubis/core/Selection/app
   python -m pytest -q setanubis/tests \
      --cov=SetAnubis --cov-config=pyproject.toml \
      --cov-report=term-missing --cov-fail-under=58
   python reproducibility/run_all.py --output-dir .ci-reproducibility
   sphinx-build -W --keep-going -b html Docs/manual/source Docs/manual/build/html
   python -m build
   python -m twine check dist/*

Release gates
-------------

The CI matrix covers Python 3.10, 3.11, 3.12 and 3.13. The Python 3.12 job also
runs the release lint, dependency audit, high-severity source scan,
reproducibility examples and coverage gate. Generated UFO code, optional Dash
applications, examples and external toolchains are excluded from the coverage
metric; the current minimum is 58 percent over the maintained production
modules.

Contract tests additionally verify the public facade, public docstrings,
interface documentation, packaged example data, documentation assets, licence
metadata and release-source cleanliness. The packaging job builds an sdist and
wheel, checks their metadata and imports the installed wheel from outside the
source tree.
