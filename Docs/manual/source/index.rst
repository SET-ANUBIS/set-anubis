SET-ANUBIS documentation
========================

.. raw:: html

   <div class="setanubis-hero">
     <img src="images/set-anubis-logo.png" alt="SET-ANUBIS logo">
   </div>

SET-ANUBIS (*Simulation, accEptance and sensiTivity studies framework for
ANUBIS*) is a modular software pipeline for long-lived-particle sensitivity
studies in the proposed ANUBIS detector.  The framework mirrors the workflow
described in the SET-ANUBIS paper: define a BSM model, compute widths and
branching ratios, generate events, ingest HepMC output, evaluate the ANUBIS
geometry acceptance and apply the truth-level selection used in sensitivity
studies.

.. raw:: html

   <div class="setanubis-callout">
     <strong>What this manual covers.</strong> The manual is organised around the
     public analysis workflow: model handling, branching ratios, generation,
     geometry-aware selection, reproducibility and release tooling.  It also
     points to the curated example suite and the optional Dash applications.
   </div>

ANUBIS context
--------------

ANUBIS is a proposed transverse LLP detector at LHC Point 1.  Its purpose is to
instrument the ATLAS underground cavern and shaft regions with RPC tracking
stations so that LLP decays missed by the main ATLAS detector can still be
observed through charged decay products.

.. image:: images/anubis-detector-concept.jpeg
   :width: 72%
   :align: center
   :alt: ANUBIS detector concept in the ATLAS cavern

SET-ANUBIS turns that detector concept into an analysis workflow: UFO models,
branching-ratio calculations, MadGraph or Pythia-driven event generation,
compact storage, geometry-aware selection and sensitivity inputs are kept in one
reproducible environment.

.. image:: images/set-anubis-architecture.jpg
   :width: 95%
   :align: center
   :alt: SET-ANUBIS software architecture

Main capabilities
-----------------

* expose a stable public Python API through ``from setanubis import ...``;
* handle widths, branching ratios and lifetimes using multiple interchangeable
  strategies;
* prepare MadGraph campaigns and optional Pythia-oriented studies;
* convert HepMC data into selection-ready dataframe bundles;
* model the ATLAS cavern, shaft regions and ANUBIS RPC station geometry;
* trace the full selection cutflow and optionally export HTML / JSON reports;
* store run metadata and compact event bundles with reproducible provenance;
* inspect events and storage through optional Dash dashboards.

Documentation contents
----------------------

.. toctree::
   :maxdepth: 2

   ProgramOverview
   Installation
   MadGraphGeneration
   SelectionWorkflow
   BranchingRatioCalculation
   Pythia
   CIAndDocs
   Reproducibility
   ReleaseUpdate
   api/public_api

Recommended import style
------------------------

The PyPI project is named ``SetAnubis``, but the recommended user-facing import
layer is the lower-case facade ``setanubis``:

.. code-block:: python

   from setanubis import (
       SetAnubisInterface,
       MadGraphCommandConfig,
       GeneralCardInterface,
       SelectionConfig,
       SelectionPipelineBuilder,
       DecayInterface,
       CalculationDecayStrategy,
       ufo_path,
   )

The internal ``SetAnubis.core`` paths remain available for advanced development,
but new analysis scripts should prefer the public facade so that they stay close
to the documented release API.

Examples and dashboards
-----------------------

The repository ships curated examples for the principal public workflows:

* ``examples/MadGraph`` for campaign setup;
* ``examples/BranchingRatio`` for widths, branching ratios and lifetimes;
* ``examples/Selection`` for HepMC ingestion, cutflows and trace reports;
* ``HepMCGUI`` and ``SetAnubisDBDashboard`` for interactive inspection.

The manual pages link directly to the relevant examples and explain the expected
inputs, outputs and external-runtime requirements.

References
----------

Please cite the software and the relevant ANUBIS detector papers when using this
framework:

* SET-ANUBIS software preprint: https://arxiv.org/abs/2512.14942
* ANUBIS proposal: https://arxiv.org/abs/1909.13022
* ANUBIS detector/sensitivity paper: https://arxiv.org/abs/2510.26932

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
