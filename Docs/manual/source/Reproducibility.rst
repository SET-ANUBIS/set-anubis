Reproducibility protocol
========================

SET-ANUBIS ships a deterministic reproducibility suite intended to accompany the
software release and the CPC program description. The suite is deliberately
smaller than a publication-scale Monte Carlo campaign: it verifies that the
scientific software path produces the expected model, decay, card-generation and
selection results from version-controlled inputs.

R1--R5 structure
----------------

The ``reproducibility/`` directory contains five independent scenarios:

.. list-table::
   :header-rows: 1

   * - ID
     - Scientific component
     - Reproduced result
     - External executable
   * - R1
     - Core/model interface
     - HNL UFO content and parameter update
     - none
   * - R2
     - Branching-ratio layer
     - partial widths, total width and branching fractions
     - none
   * - R3
     - Pythia preparation
     - deterministic ``.cmnd`` file
     - Pythia is not run
   * - R4
     - MadGraph preparation
     - process, run, parameter, shower and MadSpin cards
     - MadGraph/Docker are not run
   * - R5
     - Selection
     - HepMC conversion, cutflow and JSON/HTML trace
     - no generator is run

Every scenario follows the same directory contract:

.. code-block:: text

   R<N>_<name>/
   ├── README.md
   ├── input/
   ├── expected_output/
   ├── output/
   └── run.py

``input/`` and ``expected_output/`` are version controlled. ``output/`` is
created locally and ignored by Git. Canonical scientific resources that already
belong to the Python package are referenced from the scenario configuration
rather than copied a second time.

Running the suite
-----------------

R5 reads the packaged HepMC2 sample, so install the selection extra:

.. code-block:: bash

   python -m venv .venv
   . .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev,selection]"
   python reproducibility/run_reproducibility.py

The default run writes into each scenario's ``output/`` directory. For CI or an
archival execution, collect all outputs below one root:

.. code-block:: bash

   python reproducibility/run_reproducibility.py \
      --output-root reproducibility_outputs

A successful run writes ``VALIDATED`` markers and an aggregate
``reproducibility_results.json``. The generated ``summary.json`` for each
scenario is compared recursively against ``expected_output/summary.json``;
floating-point values use a relative and absolute tolerance of ``1e-12``.
Generated text cards are represented by SHA-256 digests.

A single scenario can also be run directly:

.. code-block:: bash

   python reproducibility/R3_pythia_cmnd/run.py
   python reproducibility/run_reproducibility.py --scenario R5

Selection input and outputs
---------------------------

R5 begins with the compact, seven-event HepMC2 gzip file distributed under
``SetAnubis.examples.Selection.InputFiles``. It rebuilds the flat event
dataframe, runs the standard geometry-aware selection and produces:

* ``events_from_hepmc.csv.gz``;
* ``selection_trace.json``;
* ``selection_trace.html``;
* ``summary.json``.

The seven events reproduce the observed cutflow outcomes in the compact sample:
failures after ``LLPDecay``, ``InCavern``, ``NotInATLAS``, ``Geometry``,
``Tracker`` and ``MET``, followed by one event that reaches ``Final``.

Continuous integration
----------------------

The dedicated ``Reproducibility`` GitHub Actions workflow runs R1--R5 on every
push and pull request to ``main`` or ``develop``. Its status check should be
required by the repository ruleset. The release workflow repeats the suite before
building or publishing distribution artifacts and uploads the generated evidence
as a GitHub Actions artifact.

Scientific scope
----------------

The suite validates deterministic software behaviour; it does not claim to
reproduce the complete event campaign of a physics publication. A full campaign
also requires the archived generator versions, container image digests, random
seeds, process definitions, cards, scan grids and larger event samples.

For a CPC submission, retain the R1--R5 output directory together with the exact
SET-ANUBIS tag, the Python environment description, the wheel/sdist checksums and
any external-tool provenance needed by the publication-scale analysis.
