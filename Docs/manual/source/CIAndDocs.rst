Documentation and CI
====================

The public repository uses GitHub Actions for continuous integration,
documentation builds, CodeQL analysis, optional Pythia-native checks and release
publishing.

Local documentation build
-------------------------

.. code-block:: bash

   python -m pip install -e ".[docs]"
   setanubis-docs --open

or directly:

.. code-block:: bash

   sphinx-build -b html Docs/manual/source Docs/manual/build/html

GitHub Pages
------------

The documentation workflow builds Sphinx HTML and deploys it to GitHub Pages when
running on the main branch or through the configured manual workflow.  In the
GitHub repository settings, Pages must use ``GitHub Actions`` as the source.  The
published site is expected at:

.. code-block:: text

   https://set-anubis.github.io/set-anubis/

Local CI equivalent
-------------------

.. code-block:: bash

   python -m pip install -e ".[dev,docs,selection,madgraph]"
   python -m compileall -q setanubis/SetAnubis setanubis/setanubis.py setanubis/__init__.py
   setanubis-pythia-smoke --out .ci-pythia-smoke
   python -m ruff check .
   python -m pip_audit
   python -m bandit -q -lll -r setanubis/SetAnubis/core \
      -x setanubis/SetAnubis/core/UFOInterface/SM_NLO,setanubis/SetAnubis/core/BranchingRatio/app,setanubis/SetAnubis/core/DataBase/app,setanubis/SetAnubis/core/Geometry/app,setanubis/SetAnubis/core/MadGraph/app,setanubis/SetAnubis/core/Pythia/app,setanubis/SetAnubis/core/Selection/app
   python -m pytest -q setanubis/tests --cov=SetAnubis --cov-config=pyproject.toml --cov-fail-under=35
   python reproducibility/run_all.py --output-dir .ci-reproducibility
   sphinx-build -W --keep-going -b html Docs/manual/source Docs/manual/build/html
   python -m build
   python -m twine check dist/*


Release gates
-------------

The Python 3.12 CI job audits installed dependencies for known vulnerabilities,
runs the high-severity source scan, and enforces a minimum 35 percent coverage over production
modules after excluding generated UFO code, GUI applications, examples and the
legacy v2 database compatibility implementation.  Contract tests also import
every symbol in the public facade, require a public docstring, inspect the
hexagonal port interfaces, and confirm that the documented lightweight examples
and data files are present in the installed package.

The packaging job installs the built wheel with its runtime dependencies in a
source-independent temporary directory.  This avoids a checkout shadowing a
missing file in the wheel.
