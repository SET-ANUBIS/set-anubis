Installation
============

SET-ANUBIS is published on PyPI as ``SetAnubis``.  The recommended Python import
layer is the lower-case facade ``setanubis``.

Quick start
-----------

.. code-block:: bash

   python -m pip install SetAnubis

For development from a local checkout:

.. code-block:: bash

   git clone https://github.com/SET-ANUBIS/set-anubis.git
   cd set-anubis
   python -m pip install -e ".[dev,docs,selection,madgraph]"
   python -m pytest -q setanubis/tests

Basic import check
------------------

.. code-block:: python

   import setanubis
   from setanubis import SetAnubisInterface, SelectionConfig, ufo_path

   print(setanubis.__version__)
   print(ufo_path("UFO_HNL"))

Optional extras
---------------

The release keeps optional features behind extras so that the base wheel remains
lightweight:

.. code-block:: bash

   python -m pip install "SetAnubis[selection]"  # HepMC ingestion and selection helpers
   python -m pip install "SetAnubis[madgraph]"   # Docker-backed MadGraph helpers
   python -m pip install "SetAnubis[app]"        # optional Dash applications
   python -m pip install "SetAnubis[docs]"       # local Sphinx build support

Pythia / HepMC3 native extension
--------------------------------

The default wheel is Python-only.  The optional native Pythia8 / HepMC3 binding
is built only when explicitly requested.

.. code-block:: bash

   SETANUBIS_BUILD_PYTHIA=1    SETANUBIS_PYTHIA8_DIR=/path/to/pythia8    SETANUBIS_HEPMC3_DIR=/path/to/hepmc3    python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"

For a local checkout, helper scripts are available to build the external copies
first:

.. code-block:: bash

   ./External_Integration/install.sh HepMC3 Pythia
   SETANUBIS_BUILD_PYTHIA=1    SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315    SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install    python -m pip install -e ".[pythia]"
   setanubis-pythia-check

See ``PYTHIA_PACKAGING.md`` for the release policy and supported build modes.

Recommended repository checks
-----------------------------

Before preparing a release or validating a local branch, the core checks are:

.. code-block:: bash

   python -m pytest -q setanubis/tests
   python -m compileall -q setanubis/SetAnubis setanubis/setanubis.py setanubis/__init__.py
   python -m bandit -q -lll -r setanubis/SetAnubis/core       -x setanubis/SetAnubis/core/UFOInterface/SM_NLO,setanubis/SetAnubis/core/BranchingRatio/app,setanubis/SetAnubis/core/DataBase/app,setanubis/SetAnubis/core/Geometry/app,setanubis/SetAnubis/core/MadGraph/app,setanubis/SetAnubis/core/Pythia/app,setanubis/SetAnubis/core/Selection/app
   setanubis-docs --strict

Asset helper functions
----------------------

The public helper functions ``asset_path()`` and ``ufo_path()`` resolve bundled
resources:

.. code-block:: python

   from setanubis import asset_path, ufo_path

   print(asset_path("Pythia/TestFiles/production_eq.py"))
   print(ufo_path("UFO_HNL"))
