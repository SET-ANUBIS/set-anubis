Installation
============

Python-only installation
------------------------

.. code-block:: bash

   python -m pip install SetAnubis

From a developer checkout:

.. code-block:: bash

   git clone https://github.com/SET-ANUBIS/set-anubis.git
   cd set-anubis
   python -m pip install -e .
   setanubis-pythia-smoke

Optional extras
---------------

.. code-block:: bash

   python -m pip install "SetAnubis[selection]"
   python -m pip install "SetAnubis[madgraph]"
   python -m pip install "SetAnubis[app]"
   python -m pip install "SetAnubis[docs]"

Native Pythia/HepMC3 runtime
----------------------------

The native Pythia binding is opt-in:

.. code-block:: bash

   SETANUBIS_BUILD_PYTHIA=1    SETANUBIS_PYTHIA8_DIR=/path/to/pythia8    SETANUBIS_HEPMC3_DIR=/path/to/hepmc3    python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"

For a local checkout, the external helper can build HepMC3 and Pythia8 first:

.. code-block:: bash

   ./External_Integration/install.sh HepMC3 Pythia
   SETANUBIS_BUILD_PYTHIA=1    SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315    SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install    python -m pip install -e ".[pythia]"

Diagnostics
-----------

.. code-block:: bash

   setanubis-pythia-check

Large samples and private assets
--------------------------------

Wheels ship lightweight assets such as UFO examples and particle data. Large
HepMC files, scan outputs and private databases should stay outside the wheel.
Set ``SETANUBIS_ASSETS_DIR=/path/to/Assets`` when you want the package to use a
custom asset directory.
