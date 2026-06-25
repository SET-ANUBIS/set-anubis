Public short-import API
=======================

The PyPI distribution is named ``SetAnubis``.  The recommended user-facing import
module is the lower-case facade ``setanubis``:

.. code-block:: python

   from setanubis import SetAnubisInterface, SelectionConfig, ufo_path

This facade is intentionally lazy: optional integrations such as Pythia/HepMC3,
Dash or Docker are not imported until the corresponding object is requested.
Internal ``SetAnubis.core`` paths remain available for advanced development and
backwards compatibility, but documentation and analysis notebooks should use
``setanubis``.

Recommended imports by workflow
-------------------------------

MadGraph generation
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from setanubis import (
       SetAnubisInterface,
       MadGraphCommandConfig,
       GeneralCardInterface,
       MadgraphInterface,
       MadGraphDockerRunner,
       MadGraphLocalRunner,
       ufo_path,
   )

Selection and geometry
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from setanubis import (
       ATLASCavern,
       GeometrySelectionAdapter,
       SelectionGeometryAdapter,
       SelectionConfig,
       RunConfig,
       MinThresholds,
       MinDR,
       SelectionPipelineBuilder,
       SelectionManager,
       EventsBundleSource,
   )

Branching ratios and lifetimes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from setanubis import (
       SetAnubisInterface,
       DecayInterface,
       CalculationDecayStrategy,
       Unit,
       ufo_path,
   )

Optional Pythia support
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from setanubis import (
       PythiaCMNDInterface,
       PythiaRunInterface,
       CMNDScanManager,
       HardProductionQCDList,
       HardProductionElectroweakList,
   )

Resource helpers
----------------

.. code-block:: python

   from setanubis import asset_path, ufo_path

   particle_database = asset_path("particles", "particleData.json")
   hnl_model = ufo_path("UFO_HNL")

These helpers resolve packaged assets after ``pip install`` and should be
preferred over hard-coded repository-relative paths.
