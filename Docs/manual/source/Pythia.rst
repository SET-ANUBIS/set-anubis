Optional Pythia support
=======================

Pythia is a supporting generation backend in the release documentation. The
MadGraph workflow is the primary public example; Pythia is kept available for
standalone samples, showering tests and cross-checks.

Two layers are exposed:

* ``PythiaCMNDInterface`` builds ``.cmnd`` cards for particles, decays,
  production channels and generic Pythia settings.
* ``PythiaRunInterface`` executes the optional C++/pybind11 runtime and supports
  particle-specific lifetimes, widths and hard cuts.

CMND generation works in the Python-only wheel. Runtime generation requires the
native binding compiled against Pythia8 and HepMC3.

CMND smoke test
---------------

.. code-block:: bash

   setanubis-pythia-smoke --pid 42 --out pythia_smoke_outputs

Runtime diagnostic
------------------

.. code-block:: bash

   setanubis-pythia-check

Native build
------------

.. code-block:: bash

   SETANUBIS_BUILD_PYTHIA=1 \
   SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
   SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
   python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"

See ``PYTHIA_PACKAGING.md`` for the full policy and troubleshooting notes.
