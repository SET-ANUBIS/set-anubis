Optional Pythia support
=======================

Pythia is documented as a supporting backend.  The main release examples use
MadGraph for signal generation and the selection layer for ANUBIS acceptance.
Pythia remains useful for standalone generation, showering tests, decay-table
cross-checks and situations where a direct Pythia8/HepMC3 workflow is preferable.

Two layers are exposed:

* ``PythiaCMNDInterface`` builds ``.cmnd`` files.  It works in a Python-only
  installation and supports particle-specific options, lifetimes, widths,
  production switches and generic Pythia settings.
* ``PythiaRunInterface`` calls the optional C++/pybind11 binding.  It requires a
  native build against external Pythia8 and HepMC3 installations.

CMND smoke test
---------------

.. code-block:: bash

   setanubis-pythia-smoke --pid 42 --out pythia_smoke_outputs

Native runtime diagnostic
-------------------------

.. code-block:: bash

   setanubis-pythia-check

Build policy
------------

The extension is not built by default on PyPI installs.  To compile it from
source:

.. code-block:: bash

   SETANUBIS_BUILD_PYTHIA=1 \
   SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
   SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
   python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"

See ``PYTHIA_PACKAGING.md`` for troubleshooting and environment-variable details.
