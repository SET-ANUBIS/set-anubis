Installation
============

SET-ANUBIS requires Python 3.10 or later. The distribution is published as
``SetAnubis`` and exposes the public import module ``setanubis``.

Standard installation
---------------------

.. code-block:: bash

   python -m pip install SetAnubis

A basic import check is:

.. code-block:: python

   import setanubis
   from setanubis import SetAnubisInterface, ufo_path

   print(setanubis.__version__)
   model = SetAnubisInterface(str(ufo_path("UFO_HNL")))

Development installation
------------------------

.. code-block:: bash

   git clone https://github.com/SET-ANUBIS/set-anubis.git
   cd set-anubis
   python -m pip install -e ".[dev,docs,selection,madgraph]"
   python -m pytest -q setanubis/tests

Optional feature groups
-----------------------

.. code-block:: bash

   python -m pip install "SetAnubis[selection]"  # HepMC and selection helpers
   python -m pip install "SetAnubis[madgraph]"   # MadGraph/Docker helpers
   python -m pip install "SetAnubis[app]"        # Dash applications
   python -m pip install "SetAnubis[docs]"       # Sphinx documentation

The default wheel does not contain the large external generator installations.
MadGraph, MARTY, Pythia8 and HepMC3 are configured separately when a workflow
requires them.

Optional Pythia8/HepMC3 extension
---------------------------------

The native interface is disabled by default. To build it, provide compatible
Pythia8 and HepMC3 installations explicitly:

.. code-block:: bash

   SETANUBIS_BUILD_PYTHIA=1 \
   SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
   SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
   python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"

A source checkout also provides a helper for local external builds:

.. code-block:: bash

   ./External_Integration/install.sh HepMC3 Pythia
   SETANUBIS_BUILD_PYTHIA=1 \
   SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
   SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
   python -m pip install -e ".[pythia]"
   setanubis-pythia-check

See ``PYTHIA_PACKAGING.md`` for the complete native-build policy.

Resource paths
--------------

Packaged resources should be resolved with the public helpers rather than with a
path relative to the current working directory:

.. code-block:: python

   from setanubis import asset_path, ufo_path

   print(asset_path("particles", "particleData.json"))
   print(ufo_path("UFO_HNL"))

Release-equivalent local checks
-------------------------------

.. code-block:: bash

   python -m pip install -e ".[dev,docs,selection,madgraph]"
   python -m compileall -q setanubis/SetAnubis setanubis/setanubis.py setanubis/__init__.py
   setanubis-pythia-smoke --out .local-pythia-smoke
   python -m ruff check .
   python -m pip_audit
   python -m pytest -q setanubis/tests \
      --cov=SetAnubis --cov-config=pyproject.toml --cov-fail-under=58
   python reproducibility/run_reproducibility.py --output-root .local-reproducibility
   setanubis-docs --strict
