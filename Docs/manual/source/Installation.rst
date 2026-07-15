Installation
============

SET-ANUBIS separates the Python analysis framework from large external HEP tools.
A normal PyPI installation is sufficient for model inspection, card construction,
branching-ratio interfaces, geometry definitions and the public selection API.
The base dependency set includes Awkward Array, FastJet, the Docker Python SDK,
Watchdog and six so that public imports and bundled examples are available immediately.
MadGraph, Pythia8, HepMC3 and MARTY remain external or optional tools
that must be configured for workflows that execute them.

Python package
--------------

.. code-block:: bash

   python -m pip install SetAnubis

From a development checkout:

.. code-block:: bash

   git clone https://github.com/SET-ANUBIS/set-anubis.git
   cd set-anubis
   python -m pip install -e ".[dev,docs,selection,madgraph]"
   python -m pytest -q setanubis/tests

The public import layer is:

.. code-block:: python

   import setanubis
   from setanubis import SetAnubisInterface, SelectionConfig, ufo_path

Optional extras
---------------

.. code-block:: bash

   python -m pip install "SetAnubis[selection]"  # adds pyhepmc
   python -m pip install "SetAnubis[madgraph]"   # compatibility extra; Docker SDK is in the base install
   python -m pip install "SetAnubis[app]"        # Dash inspection tools
   python -m pip install "SetAnubis[docs]"       # Sphinx documentation

MadGraph
--------

MadGraph is the primary generation backend shown in the release documentation.
SET-ANUBIS can generate the cards and job scripts; execution can happen in a
local installation, in Docker, or on a batch system.

.. code-block:: bash

   ./External_Integration/install.sh MadGraph
   python -m pip install -e ".[madgraph]"

External installations are also supported; the framework only needs to know where
MadGraph is executed and where the resulting ``Events`` directory is stored.

Optional Pythia/HepMC3 binding
------------------------------

The native Pythia runtime is intentionally opt-in.  CMND card generation works in
the Python-only install, but runtime generation requires a compiled extension
linked against Pythia8 and HepMC3.

.. code-block:: bash

   SETANUBIS_BUILD_PYTHIA=1 \
   SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
   SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
   python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"

From a checkout:

.. code-block:: bash

   ./External_Integration/install.sh HepMC3 Pythia
   SETANUBIS_BUILD_PYTHIA=1 \
   SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
   SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
   python -m pip install -e ".[pythia]"
   setanubis-pythia-check

Assets and private UFOs
-----------------------

The wheel ships lightweight assets and example UFOs.  For private models or
large generated samples, keep them outside the wheel and point SET-ANUBIS to the
asset directory explicitly:

.. code-block:: bash

   export SETANUBIS_ASSETS_DIR=/path/to/Assets

Then use:

.. code-block:: python

   from setanubis import asset_path, ufo_path

   hnl_ufo = ufo_path("UFO_HNL")
   particles = asset_path("particles", "particleData.json")

Reproducibility examples
------------------------

The source release contains the CPC-oriented validation examples described in
:doc:`Reproducibility`. They run after a normal editable installation and do not
start external generators.
