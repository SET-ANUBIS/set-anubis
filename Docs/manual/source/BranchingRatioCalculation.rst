Branching ratios, widths and lifetimes
======================================

The branching-ratio layer provides a common interface for quantities that enter
both generation and sensitivity projections: partial widths, total widths,
branching ratios and lifetimes.  In an LLP scan these values often depend on the
same model parameters that control production kinematics, such as an HNL mass or
mixing angle.

Role in the analysis
--------------------

The layer is used to:

* provide model-dependent widths to parameter cards or generator metadata;
* tabulate branching ratios over scan parameters;
* compute lifetimes for selection and optional decay-position reweighting;
* prepare decay information for MadSpin or optional Pythia card generation;
* compare calculation strategies during validation.

Available strategies
--------------------

``CalculationDecayStrategy`` currently exposes:

* ``PYTHON`` for user-defined formulas;
* ``FILE_INTERPOLATION`` for tabulated widths or branching ratios;
* ``UFO`` for UFO-based calculations;
* ``MADGRAPH`` for generator-assisted width extraction;
* ``MARTY`` for MARTY-oriented symbolic/numeric workflows.

HNL-style example
-----------------

.. code-block:: python

   from setanubis import (
       SetAnubisInterface,
       DecayInterface,
       CalculationDecayStrategy,
       Unit,
       ufo_path,
   )

   model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
   model.set_leaf_param("mN1", 1.0)
   model.set_leaf_param("VeN1", 1.0e-6)

   decays = DecayInterface(model)
   decays.add_decays(
       [
           {"mother": 25, "daughters": [-13, 13]},
           {"mother": 25, "daughters": [22, 22]},
       ],
       CalculationDecayStrategy.FILE_INTERPOLATION,
       {
           "file_path": "br_table.csv",
           "varying_params": ["mN1", "VeN1"],
           "format_type": "csv",
       },
   )

   print(decays.get_brs(25))
   print(decays.calculate_lifetime(25, Unit.S))

The concrete test file used by the repository is
``setanubis/SetAnubis/examples/BranchingRatio/example_BranchingRatioInterface_hnl.py``.

Connection to generation
------------------------

For MadGraph/MadSpin studies the branching-ratio layer is not required to launch
a process, but it is useful for keeping the scan metadata physically consistent:
widths, decay tables and sensitivity factors can all be evaluated from the same
model-parameter state.  For optional Pythia workflows the same information can be
translated into ``.cmnd`` decay configuration.

Developer examples
------------------

The extended examples in
``setanubis/SetAnubis/examples/BranchingRatio/dev_examples`` cover every
supported preparation path without hiding external-runtime requirements:

* ``example_manual_values_and_lifetime.py`` registers externally calculated
  widths or direct branching ratios and derives a lifetime;
* ``example_python_calculator.py`` loads a trusted Python
  ``IDecayCalculation`` implementation;
* ``example_file_interpolation.py`` performs linear interpolation inside a CSV
  parameter grid;
* ``example_ufo_decay_functions.py`` inspects decay functions extracted from a
  trusted UFO model;
* ``example_madgraph_preparation.py`` writes MadGraph width-command, run and
  parameter cards without launching MadGraph or Docker;
* ``example_marty_preparation.py`` renders an analytic MARTY C++ source file
  without compiling or executing MARTY.

Run an example from the repository root, for example:

.. code-block:: bash

   python setanubis/SetAnubis/examples/BranchingRatio/dev_examples/example_file_interpolation.py
   python setanubis/SetAnubis/examples/BranchingRatio/dev_examples/example_madgraph_preparation.py --output-dir prepared_widths
   python setanubis/SetAnubis/examples/BranchingRatio/dev_examples/example_marty_preparation.py --output prepared_marty/z_to_ddbar.cpp

Python calculators and UFO models are executable Python inputs. Only use files
from trusted sources. The MadGraph and MARTY preparation examples generate
inputs but deliberately do not execute those external programs.
