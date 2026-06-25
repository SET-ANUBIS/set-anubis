SET-ANUBIS documentation
========================

SET-ANUBIS is a modular Python/C++ framework for ANUBIS long-lived-particle
sensitivity studies. The release documentation follows the main analysis
workflow: model/UFO input, MadGraph generation, database ingestion, geometry,
selection, branching ratios and optional Pythia support.

.. image:: images/set-anubis-architecture.pdf
   :width: 95%
   :alt: SET-ANUBIS architecture

Contents
--------

.. toctree::
   :maxdepth: 2

   Installation
   MadGraphGeneration
   SelectionWorkflow
   BranchingRatioCalculation
   CIAndDocs
   ReleaseUpdate
   Pythia
   api/public_api

Public API
----------

For user scripts and notebooks, prefer short imports:

.. code-block:: python

   from setanubis import (
       SetAnubisInterface,
       MadGraphCommandConfig,
       GeneralCardInterface,
       SelectionConfig,
       SelectionPipelineBuilder,
       DecayInterface,
       ufo_path,
   )

The internal ``SetAnubis.core`` paths remain available for advanced use, but the
short API is the stable public entry point for examples and documentation.

Citation
--------

Please cite the software and the associated preprint placeholder:
https://arxiv.org/abs/2512.14942

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
