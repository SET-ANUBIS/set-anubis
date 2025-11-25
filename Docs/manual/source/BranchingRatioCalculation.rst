.. _BRcalculator:

Branching Ratio Calculation Interface
=====================================

The **Branching Ratio (BR)** interface provides a powerful and extensible way to define, validate, and compute decay widths and branching ratios for particles using several computational strategies. This tool is ideal for studying long-lived particles (LLPs) and more generally any particle model defined via UFO format.

Overview
--------

This interface supports:

- Defining decay channels using physical conservation laws
- Computing:
  - Partial decay widths
  - Total widths
  - Branching ratios (BRs)
- Multiple calculation backends:
  - Python analytical functions
  - Interpolation from external files (CSV, etc.)
  - UFO-based analytical tools
  - MadGraph interface
  - Marty symbolic engine

Usage
-----

To use the branching ratio tools, you typically interact with the `DecayInterface` class:

.. code-block:: python

    from SetAnubis.core.ModelCore.adapters.input.NeoSetAnubisInteface import SetAnubisInterface
    from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface
    from SetAnubis.core.BranchingRatio.domain.calculation_strategy import CalculationDecayStrategy

    nsa = NeoSetAnubisInterface("db/HNL/UFO_HNL")
    decay_interface = DecayInterface(nsa)

Defining Decay Channels
------------------------

To register decay channels, use the `add_decays` method:

.. code-block:: python

    decay_list = [
        {"mother": 9900012, "daughters": [12, -12, 12]},
        {"mother": 9900012, "daughters": [-11, 11, 12]}
    ]

    config = {"script_path": "path/to/my_decay_script.py"}

    decay_interface.add_decays(decay_list, CalculationDecayStrategy.PYTHON, config)

Available Calculation Strategies
--------------------------------

The interface supports several strategies for computing decay widths:

- **PYTHON**: User-defined Python scripts implementing `IDecayCalculation`.
- **FILE_INTERPOLATION**: CSV or other formats with precomputed decay data.
- **UFO**: Use UFO+FeynRules-style calculations.
- **MADGRAPH**: Call external MadGraph instances.
- **MARTY**: Use symbolic manipulation for BR estimation (requires Marty).

Example for each:

**Python strategy:**

.. code-block:: python

    config = {"script_path": "decay_models/HNL_decay_model.py"}
    decay_interface.add_decays(decay_list, CalculationDecayStrategy.PYTHON, config)

**File Interpolation strategy (CSV):**

.. code-block:: python

    config = {
        "file_path": "results/BR_table.csv",
        "varying_params": ["mN1", "Ve"],
        "format_type": "csv"
    }
    decay_interface.add_decays(decay_list, CalculationDecayStrategy.FILE_INTERPOLATION, config)

**UFO strategy:**

.. code-block:: python

    config = {"ufo_path": "db/HNL/UFO_HNL"}
    decay_interface.add_decays(decay_list, CalculationDecayStrategy.UFO, config)

BR Calculation Types
--------------------

Once decays are registered, you can calculate:

- **Partial decay width**:

.. code-block:: python

    from SetAnubis.core.Common.multi_set import MultiSet

    width = decay_interface.get_decay(9900012, MultiSet([12, -12, 12]))

- **Total decay width**:

.. code-block:: python

    total_width = decay_interface.get_decay_tot(9900012)

- **All branching ratios for a mother**:

.. code-block:: python

    brs = decay_interface.get_brs(9900012)

    for entry in brs:
        print(entry["daughters"], entry["branching_ratio"])

- **Branching ratio for a specific channel**:

.. code-block:: python

    br = decay_interface.get_br(9900012, MultiSet([12, -12, 12]))

Decay Validity and Error Checking
---------------------------------

All decays are validated before registration:

- **Charge conservation** is enforced via the `DecayChecker`.
- If a decay violates charge conservation or mass thresholds, an error is raised.

Example of invalid decay:

.. code-block:: python

    decay_list = [
        {"mother": 9900012, "daughters": [11, 11]}  # ⚠️ invalid if charge not conserved
    ]

    # This will raise a ValueError
    decay_interface.add_decays(decay_list, CalculationDecayStrategy.PYTHON, config)

Extending with Custom Calculators
---------------------------------

To define your own decay calculator:

1. Create a class implementing `IDecayCalculation`.
2. Implement the `calculate(self, mother, daughters, parameters)` method.
3. Return the decay width as a float.

Example:

.. code-block:: python

    from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation

    class MyCustomDecay(IDecayCalculation):
        def calculate(self, mother, daughters, parameters):
            return 0.1  # toy example

4. Point to the script via:

.. code-block:: python

    config = {"script_path": "path/to/my_script.py"}
    decay_interface.add_decays(..., CalculationDecayStrategy.PYTHON, config)

Dynamic Parameters and Particle Properties
------------------------------------------

All particle masses and parameters are obtained from the `NeoSetAnubisInterface`. You can update model parameters like:

.. code-block:: python

    nsa.set_leaf_param("mN1", 1.0)
    nsa.set_leaf_param("Ve", 1e-2)

To fetch full parameter dictionary:

.. code-block:: python

    all_params = nsa.get_all_parameters()

MultiSet Utility
----------------

Daughter particles are passed using `MultiSet`, which accounts for multiplicity:

.. code-block:: python

    from SetAnubis.core.Common.multi_set import MultiSet

    ms = MultiSet([12, -12, 12])
    # Represents two 12 and one -12

CLI Interface (Optional)
-------------------------

You can also expose your pipeline via CLI using a config YAML:

.. code-block:: bash

    python cli_br.py --config my_config.yaml --param Ve=1e-3 --param mN1=0.5

Where the YAML might look like:

.. code-block:: yaml

    model: db/HNL/UFO_HNL
    strategy: PYTHON
    strategy_config:
      script_path: scripts/decay_hnl.py
    decays:
      - mother: 9900012
        daughters: [12, -12, 12]
    mass: 1.0
    parameters:
      Ve: 1e-2
      Vmu: 1e-3

Conclusion
----------

The Branching Ratio interface is designed to be:

✅ Extensible  
✅ Physically robust (with conservation checks)  
✅ Compatible with multiple backends  
✅ CLI and YAML compatible for automation workflows  

It's an essential tool in simulating and analyzing decays in BSM models with long-lived particles, seamlessly integrated with the NeoSetAnubis framework.

