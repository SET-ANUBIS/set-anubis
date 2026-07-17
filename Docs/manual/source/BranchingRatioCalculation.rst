Branching ratios, widths and lifetimes
======================================

Decay properties enter several stages of an LLP analysis. They determine the
lifetime and decay probability of the LLP, the relative population of final
states, the widths written to generator cards and the normalisation factors used
in sensitivity calculations. SET-ANUBIS provides one interface for these
quantities so that they can be evaluated from the same model-parameter state.

Quantities and conventions
--------------------------

For a mother particle with partial widths :math:`\Gamma_i`, the total width and
branching ratio are

.. math::

   \Gamma_{\mathrm{tot}} = \sum_i \Gamma_i,
   \qquad
   \mathrm{BR}_i = \frac{\Gamma_i}{\Gamma_{\mathrm{tot}}}.

The proper lifetime is obtained from the total width through
:math:`\tau = \hbar/\Gamma_{\mathrm{tot}}`, with explicit unit conversions
provided by the public interface.

Calculation strategies
----------------------

``CalculationDecayStrategy`` supports several sources of decay information:

``PYTHON``
   A trusted Python implementation of ``IDecayCalculation``. This is useful for
   compact analytic expressions or model-specific calculations.

``FILE_INTERPOLATION``
   A tabulated grid of widths or branching ratios. Interpolation is restricted
   to the covered parameter domain; extrapolation is not performed silently.

``UFO``
   Decay functions or model information supplied by a trusted UFO package.

``MADGRAPH``
   Preparation of generator inputs for width extraction.

``MARTY``
   Generation of symbolic/numeric C++ sources for a MARTY-based calculation.

The different strategies can be compared for validation or combined when a
single model contains channels best described by different methods.

HNL-oriented example
--------------------

.. code-block:: python

   from setanubis import (
       SetAnubisInterface,
       DecayInterface,
       CalculationDecayStrategy,
       Unit,
       ufo_path,
   )

   model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
   model.set_parameter("mN1", 1.5)
   model.set_parameter("VeN1", 1.5)

   decays = DecayInterface(model)
   decays.add_decays(
       [{"mother": 25, "daughters": [-13, 13]}],
       CalculationDecayStrategy.FILE_INTERPOLATION,
       {
           "file_path": "br_table.csv",
           "varying_params": ["mN1", "VeN1"],
           "format_type": "csv",
       },
   )

   print(decays.get_decay(25, [-13, 13]))
   print(decays.get_brs(25))
   print(decays.calculate_lifetime(25, Unit.S))

A complete repository example is available at
``setanubis/SetAnubis/examples/BranchingRatio/example_BranchingRatioInterface_hnl.py``.

Connection to generation and selection
--------------------------------------

The decay layer can populate widths and decay tables used by MadGraph, MadSpin
or Pythia command files. The same lifetime can be recorded with the scan point
and used in lifetime reweighting or sensitivity calculations. This avoids a
common source of inconsistency in which generation and analysis use different
parameter values or decay tables.

Developer examples
------------------

The directory ``setanubis/SetAnubis/examples/BranchingRatio/dev_examples``
contains one focused example for each supported workflow:

* ``example_manual_values_and_lifetime.py`` — explicit widths or branching
  ratios and lifetime conversion;
* ``example_python_calculator.py`` — trusted Python calculator;
* ``example_file_interpolation.py`` — interpolation inside a CSV parameter grid;
* ``example_ufo_decay_functions.py`` — numerical evaluation of UFO decay
  functions;
* ``example_madgraph_preparation.py`` — MadGraph commands and cards without
  execution;
* ``example_marty_preparation.py`` — MARTY C++ source generation without
  compilation or execution.

.. code-block:: bash

   python setanubis/SetAnubis/examples/BranchingRatio/dev_examples/example_file_interpolation.py
   python setanubis/SetAnubis/examples/BranchingRatio/dev_examples/example_madgraph_preparation.py --output-dir prepared_widths
   python setanubis/SetAnubis/examples/BranchingRatio/dev_examples/example_marty_preparation.py --output prepared_marty/z_to_ddbar.cpp

Python calculators and UFO packages are executable inputs. Only load files from
a trusted source. The MadGraph and MARTY examples prepare inputs but deliberately
do not launch either external program.
