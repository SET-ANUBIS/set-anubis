SET-ANUBIS documentation
========================

SET-ANUBIS (*Simulation, accEptance and sensiTivity studies framework for
ANUBIS*) is a framework for long-lived-particle (LLP) sensitivity studies in the
proposed ANUBIS detector.  The documentation follows the analysis logic used in
the SET-ANUBIS paper: model input, branching ratios and lifetimes, MadGraph
signal generation, event ingestion, ATLAS-cavern/ANUBIS geometry, selection
cutflows and sensitivity inputs.

ANUBIS context
--------------

ANUBIS is a proposed transverse LLP detector at LHC Point 1.  The detector would
instrument the ATLAS underground cavern with RPC tracking stations so that LLPs
escaping the inner ATLAS detector could be observed through charged decay
products in the cavern volume.

.. image:: images/anubis-detector-concept.jpeg
   :width: 70%
   :align: center
   :alt: ANUBIS detector concept in the ATLAS cavern

The SET-ANUBIS framework is designed to make this detector geometry usable in
model scans.  It connects model parameters, generator cards, branching ratios,
event storage and geometry-aware selections into one reproducible workflow.

.. image:: images/set-anubis-architecture.jpg
   :width: 95%
   :align: center
   :alt: SET-ANUBIS software architecture

Documentation contents
----------------------

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

Recommended import style
------------------------

The PyPI project is named ``SetAnubis``, but the public facade used in examples
is the lower-case module ``setanubis``:

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

The internal ``SetAnubis.core`` paths are still available for backwards
compatibility and advanced development, but new analysis scripts should prefer
``from setanubis import ...``.

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
