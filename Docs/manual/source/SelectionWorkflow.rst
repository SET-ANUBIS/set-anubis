Selection workflow
==================

After event generation, SET-ANUBIS converts HepMC events or compact database
bundles into analysis-ready dataframes and applies geometry, kinematic,
isolation, jet and lifetime-reweighting cutflows.

The core objects are:

* ``ATLASCavern`` and geometry adapters for ANUBIS/ATLAS-cavern acceptance;
* ``SelectionConfig`` and ``RunConfig`` for thresholds and runtime behaviour;
* ``SelectionPipelineBuilder`` for dataframe-to-cutflow processing;
* ``SelectionManager`` for one or many samples.

Minimal cutflow skeleton
------------------------

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

   cavern = ATLASCavern()
   geometry = SelectionGeometryAdapter(GeometrySelectionAdapter(cavern))

   selection = SelectionConfig(
       geometry=geometry,
       minMET=30.0,
       minP=MinThresholds(LLP=0.1, chargedTrack=0.1, neutralTrack=0.1, jet=0.1),
       minPt=MinThresholds(LLP=0.0, chargedTrack=5.0, neutralTrack=5.0, jet=15.0),
       minDR=MinDR(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
       nStations=2,
       nIntersections=2,
       nTracks=1,
   )

   pipeline = (
       SelectionPipelineBuilder()
       .set_options(add_jets=True, compute_isolation=True, selection_mode="standard")
       .build()
   )

   source = EventsBundleSource.from_bundle_file("sample_bundle.pkl.gz")
   result = SelectionManager(pipeline).run_many(
       named_sources=[("scan-point", source)],
       sel_cfg=selection,
       run_cfg=RunConfig(reweightLifetime=False, plotTrajectory=False),
   )
   print(result.cutflow_sum)

Database integration
--------------------

The event database stores generation metadata, cards, banners, scan information
and compact dataframe bundles. Selection can therefore work on lightweight,
reproducible bundles while keeping a route back to the original HepMC run when a
full event record is needed.

Recommended examples
--------------------

* ``setanubis/SetAnubis/examples/Selection/example_df_creation.py``
* ``setanubis/SetAnubis/examples/Selection/example_df_to_sampledfs.py``
* ``setanubis/SetAnubis/examples/Selection/example_selection_pipeline.py``
* ``setanubis/SetAnubis/examples/Selection/example_jets_and_pT_deltaR_cuts.py``
