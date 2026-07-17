Optional Pythia support
=======================

Pythia is provided as a supporting backend rather than as the only route through
the framework. The documented production workflow uses MadGraph for hard-process
generation and the SET-ANUBIS selection layer for detector acceptance. Pythia
remains useful for showering and hadronisation, standalone generation,
decay-table cross-checks and studies in which a direct Pythia8/HepMC3 interface
is preferred.

Two levels of support are available.

Command-file construction
-------------------------

``PythiaCMNDInterface`` creates Pythia ``.cmnd`` files in a Python-only
installation. The interface can configure beam conditions, event counts,
particle properties, widths, lifetimes, production switches and decay channels.
It is therefore suitable for card preparation and reproducibility tests even
when the native Pythia library is not installed.

.. code-block:: bash

   setanubis-pythia-smoke --pid 42 --out pythia_smoke_outputs

The command writes and validates a small command file without starting a Pythia
run.

Native runtime
--------------

``PythiaRunInterface`` uses the optional C++/pybind11 extension and requires
compatible external Pythia8 and HepMC3 installations. The installation can be
checked with:

.. code-block:: bash

   setanubis-pythia-check

The extension is built only when explicitly requested:

.. code-block:: bash

   SETANUBIS_BUILD_PYTHIA=1 \
   SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
   SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
   python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"

The separate ``Optional Pythia binding`` GitHub workflow compiles the external
dependencies and runs a small native event-generation test. See
``PYTHIA_PACKAGING.md`` for build details and troubleshooting.
