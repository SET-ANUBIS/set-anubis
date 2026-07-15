Reproducibility package
=======================

SET-ANUBIS 1.0.0 includes a lightweight reproducibility package in the repository
root under ``reproducibility/``.  It is intended both for release validation and
for the planned *Computer Physics Communications* software submission.

The package produces deterministic outputs for five framework components:

* ModelCore: parse the bundled HNL UFO, inspect its content and update ``mN1``;
* branching ratios: interpolate two partial widths without invoking MARTY;
* Pythia: generate and validate a generic ``.cmnd`` card without the native
  Pythia8/HepMC3 runtime;
* MadGraph: generate command, run, parameter, Pythia8 and MadSpin cards without
  launching MadGraph or Docker;
* selection: build the standard sample dataframes from the bundled
  ``hnl_df.csv`` input.

Run all examples
----------------

From a source checkout:

.. code-block:: bash

   python -m venv .venv
   . .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e .
   python reproducibility/run_all.py --output-dir reproducibility_outputs

A successful run creates ``reproducibility_outputs/VALIDATED``.  The combined
``results.json`` is compared to the version-controlled
``reproducibility/expected_results.json``. Numerical values use a relative
comparison tolerance of ``1e-12``; generated cards and the selected LLP table are
identified by SHA-256 hashes.

Inputs
------

The examples use only inputs shipped with the source distribution:

* ``SetAnubis/assets/UFO/UFO_HNL``;
* ``SetAnubis/examples/BranchingRatio/TestFiles/test_BR.csv``;
* ``SetAnubis/examples/Selection/InputFiles/hnl_df.csv``.

The selection example reads CSV and deliberately does not load a pickle. UFO
models are executable Python definitions and must still be obtained from a
trusted source; see :doc:`Installation` and the repository ``SECURITY.md``.

Scope and external generators
-----------------------------

The reproducibility package verifies deterministic software behavior and card
construction. It does not reproduce large production campaigns or publication
plots. Full physics production still requires the separately configured
MadGraph, MARTY, Pythia8/HepMC3 and analysis environments, together with the
corresponding version pins, cards, seeds and archived event samples.
