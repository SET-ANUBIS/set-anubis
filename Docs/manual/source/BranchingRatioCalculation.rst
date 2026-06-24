Branching ratios and lifetimes
==============================

The branching-ratio layer provides a common interface for decay widths,
branching ratios and lifetimes. It is designed to support multiple calculation
strategies without forcing the rest of the pipeline to know whether a value came
from a Python function, an interpolation table, a UFO/MadGraph calculation or a
MARTY-oriented backend.

Typical use cases are:

* filling MadSpin and analysis metadata with model-dependent widths;
* producing branching-ratio tables for scans;
* providing decay tables to optional Pythia ``.cmnd`` card generation;
* validating toy models such as HNL benchmarks.

Minimal example
---------------

.. code-block:: python

   from setanubis import SetAnubisInterface, DecayInterface, CalculationDecayStrategy, ufo_path

   model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
   br = DecayInterface(model)

   br.add_decays(
       [{"mother": 25, "daughters": [-13, 13]}],
       CalculationDecayStrategy.FILE_INTERPOLATION,
       {
           "file_path": "br_table.csv",
           "varying_params": ["mN1", "VeN1"],
           "format_type": "csv",
       },
   )

   print(br.get_brs(25))

Available strategies
--------------------

``CalculationDecayStrategy`` currently exposes:

* ``PYTHON`` for user-defined Python implementations;
* ``FILE_INTERPOLATION`` for tabulated widths or branching ratios;
* ``UFO`` for UFO-based calculations;
* ``MADGRAPH`` for generator-assisted widths;
* ``MARTY`` for symbolic/numeric calculations through MARTY workflows.

Recommended examples
--------------------

* ``setanubis/SetAnubis/examples/BranchingRatio/example_BranchingRatioInterface_hnl.py``
