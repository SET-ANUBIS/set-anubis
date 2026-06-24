Public short-import API
=======================

The stable user-facing imports are exposed through ``setanubis`` and
``SetAnubis``.  The modules use lazy imports so that optional integrations such
as Pythia/HepMC3 are not imported until they are explicitly requested.

Recommended imports
-------------------

.. code-block:: python

   from setanubis import (
       SetAnubisInterface,
       MadGraphInterface,
       MadGraphCommandConfig,
       GeneralCardInterface,
       SelectionConfig,
       SelectionPipelineBuilder,
       SelectionEngine,
       DecayInterface,
       CalculationDecayStrategy,
       asset_path,
       ufo_path,
   )

Core workflow objects
---------------------

MadGraph generation
   ``MadGraphInterface``, ``MadgraphInterface``, ``MadGraphCommandConfig``,
   ``GeneralCardInterface``, ``RunCardBuilder``, ``ParamCardBuilder``,
   ``JobScriptBuilder``, ``PythiaCardBuilder``, ``MadSpinCardAdapter``.

Selection and geometry
   ``SelectionConfig``, ``SelectionEngine``, ``SelectionPipelineBuilder``,
   ``SelectionManager``, ``RunConfig``, ``MinThresholds``, ``MinDR``,
   ``EventsBundleSource``, ``SelectionGeometryAdapter``,
   ``GeometrySelectionAdapter``, ``ATLASCavern``, ``ATLASCavernGeometry``.

Branching ratios and model input
   ``SetAnubisInterface``, ``DecayInterface``, ``DecayBuilder``,
   ``DecayChannel``, ``CalculationDecayStrategy``, ``PartialDecayChannel``.

Optional Pythia support
   ``PythiaCMNDInterface``, ``PythiaRunInterface``, ``CMNDScanManager``,
   ``HardProductionQCDList``, ``HardProductionElectroweakList``.

Resource helpers
----------------

.. code-block:: python

   from setanubis import asset_path, ufo_path

   particle_database = asset_path("particles", "particleData.json")
   hnl_model = ufo_path("SM_HeavyN_NLO")

These helpers resolve packaged assets after ``pip install`` and should be
preferred over hard-coded repository-relative paths.
