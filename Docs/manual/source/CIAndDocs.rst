CI and documentation workflows
==============================

Local CI commands
-----------------

Run the same core checks as the GitHub CI workflow:

.. code-block:: bash

   python -m pip install -e ".[dev,docs]"
   python -m compileall -q setanubis/SetAnubis setanubis/setanubis.py setanubis/__init__.py
   setanubis-pythia-smoke --out .local-pythia-smoke
   python -m pytest -q setanubis/tests

Packaging smoke test:

.. code-block:: bash

   python -m pip install build twine
   python -m build
   twine check dist/*
   tmpdir=$(mktemp -d)
   python -m pip install --force-reinstall --no-deps dist/*.whl
   cd "$tmpdir"
   python -c "import setanubis; print(setanubis.__version__)"

Local documentation
-------------------

.. code-block:: bash

   python -m pip install -e ".[docs]"
   setanubis-docs --open

or directly:

.. code-block:: bash

   sphinx-build -b html Docs/manual/source Docs/manual/build/html

GitHub Pages deployment
-----------------------

The documentation workflow always builds HTML and uploads it as an Actions
artifact. Deployment to Pages is intentionally gated to avoid failing on fresh
repositories where Pages has not yet been enabled.

To enable deployment:

1. Open repository settings on GitHub.
2. Go to **Pages**.
3. Set **Build and deployment / Source** to **GitHub Actions**.
4. Create a repository Actions variable named ``DEPLOY_GITHUB_PAGES`` with value
   ``true``.
5. Re-run the ``Docs`` workflow or push to ``main``.

You can also run ``Docs`` manually and set ``deploy_pages=true``.
