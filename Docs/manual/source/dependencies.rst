Dependencies
============

The base SetAnubis 1.0.0 installation declares the Python libraries needed by
its public import facade and lightweight examples, including NumPy, pandas,
SciPy, SymPy, Matplotlib, PyYAML, Particle, Graphviz, Awkward Array, Docker SDK,
FastJet, Watchdog and six.

Optional extras install integrations that require additional Python bindings:

.. code-block:: bash

   python -m pip install "SetAnubis[selection]"  # adds pyhepmc
   python -m pip install "SetAnubis[pythia]"     # pybind11 and pyhepmc
   python -m pip install "SetAnubis[app]"        # Dash inspection applications
   python -m pip install "SetAnubis[docs]"       # Sphinx documentation

MadGraph, MARTY, Pythia8, HepMC3 and the Docker daemon are external programs and
are not downloaded or started by a normal Python package installation.
