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
   python -m pytest -q setanubis/tests
   python reproducibility/run_all.py --output-dir .ci-reproducibility
   sphinx-build -W --keep-going -b html Docs/manual/source Docs/manual/build/html
   python -m build
   python -m twine check dist/*
