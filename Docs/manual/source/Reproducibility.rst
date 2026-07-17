Reproducibility and validation examples
=======================================

The repository contains a lightweight reproducibility package under
``reproducibility/``. Its purpose is to verify the deterministic parts of the
software release without requiring a large Monte Carlo campaign or external
generator installation.

Covered workflows
-----------------

The validation package exercises five components:

* **model interface** — load the bundled HNL UFO, inspect model content and
  modify ``mN1``;
* **branching ratios** — interpolate partial widths from a version-controlled
  table without invoking MARTY;
* **Pythia** — construct and validate a ``.cmnd`` file without the native
  Pythia8/HepMC3 runtime;
* **MadGraph** — construct process commands, run, parameter, Pythia8 and MadSpin
  cards without launching MadGraph or Docker;
* **selection** — run the standard analysis objects and cutflow using the
  compact real-event HNL sample distributed with the package.

Running the validation
----------------------

.. code-block:: bash

   python -m venv .venv
   . .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e .
   python reproducibility/run_all.py --output-dir reproducibility_outputs

A successful run creates ``reproducibility_outputs/VALIDATED``. The combined
``results.json`` is compared with
``reproducibility/expected_results.json``. Numerical values are compared with a
relative tolerance of ``1e-12``; generated cards and selected tables are
identified by SHA-256 digests.

Distributed inputs
------------------

Only small, version-controlled inputs are used:

* the bundled HNL UFO model;
* the branching-ratio interpolation table;
* the seven-event real HNL selection sample and its provenance manifest.

The selection data are supplied in aligned HepMC, compressed CSV and trusted
compressed-pickle representations. The deterministic reproducibility test uses
the exchange-friendly compressed CSV. Pickles should only be loaded when their
origin is trusted; see the repository ``SECURITY.md``.

Scope
-----

These checks validate software behaviour, card construction and the analysis
cutflow. They do not reproduce a complete publication-scale event campaign.
Physics production still requires the relevant MadGraph, MARTY, Pythia8/HepMC3
and analysis environments, together with their versions, cards, image digests,
random seeds and archived benchmark samples.

For a scientific release, the reproducibility outputs should be retained with
the tag, source archive and distribution checksums. Larger production artefacts
can be referenced through the event catalogue or an external archival service
rather than included in the Python wheel.
