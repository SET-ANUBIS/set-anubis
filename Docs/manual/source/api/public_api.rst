Public short-import API
=======================

The recommended public entry points are exposed through ``setanubis`` and
``SetAnubis``.  Objects are imported lazily so Python-only installations do not
fail when optional integrations such as Pythia/HepMC3 are unavailable.

.. automodule:: setanubis
   :members:
   :undoc-members:

Common imports
--------------

.. code-block:: python

   from setanubis import (
       SetAnubisInterface,
       PythiaCMNDInterface,
       PythiaRunInterface,
       ATLASCavern,
       SelectionConfig,
       SelectionEngine,
       asset_path,
       ufo_path,
   )
