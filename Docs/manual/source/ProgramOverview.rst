Program overview
================

SET-ANUBIS is designed as a modular pipeline for LLP sensitivity studies in the
proposed ANUBIS detector.  The software paper describes two guiding goals:

* keep the physics workflow end-to-end, from model parameters to selection
  acceptance;
* keep the code architecture modular, testable and replaceable.

Those two goals shape the repository layout and the public API.

End-to-end analysis flow
------------------------

A typical study proceeds as follows:

1. **Model definition** – load a UFO model and set scan parameters through the
   public model interface.
2. **Decay information** – compute or prepare widths, branching ratios and
   lifetimes using a Python calculator, interpolation table, UFO-derived helper,
   MadGraph preparation or MARTY preparation.
3. **Event generation** – prepare MadGraph cards and commands, or use the
   optional Pythia-oriented tools for dedicated workflows.
4. **Event ingestion** – convert HepMC outputs into dataframe-based objects and,
   when useful, store compact selection-ready bundles.
5. **Geometry and selection** – propagate LLP decays through the ATLAS cavern /
   ANUBIS geometry, apply the truth-level cutflow, and optionally capture a full
   stage-by-stage trace.
6. **Sensitivity inputs** – combine acceptance with luminosity, production cross
   section, branching fractions and signal-efficiency assumptions.

Architecture and design principles
----------------------------------

The code follows a ports-and-adapters style (often called hexagonal
architecture).  Domain code aims to describe *what* the framework should do,
while adapters encapsulate *how* it talks to files, external tools, or storage
formats.

This has several practical benefits for a release-quality scientific codebase:

* domain objects remain easier to test in isolation;
* workflows can swap calculation or generation backends without rewriting the
  whole pipeline;
* the public API stays relatively stable even when internal adapters evolve;
* examples and validation tests can target domain behaviour rather than the
  quirks of one external executable.

Main subsystems
---------------

``SetAnubis`` exposes several user-visible subsystems:

* **Model core** – public access to UFO parameters and particle content.
* **Branching ratio layer** – widths, partial widths, branching ratios and
  lifetimes.
* **MadGraph layer** – scan-aware card generation and command preparation.
* **Selection layer** – HepMC ingestion, dataframe bundles, geometry cuts,
  isolation and trace reporting.
* **Database layer** – content-addressed artifacts, scan metadata and compact
  event bundles.
* **Dash applications** – one app for event-level HepMC / geometry inspection
  and one app for database auditing and storage analysis.

Examples as release assets
--------------------------

The example suite is a first-class part of the release.  It is intended to show
realistic usage patterns rather than only minimal import smoke tests.  In the
current release this includes:

* branching-ratio developer examples for manual values, Python calculators,
  interpolation, UFO helpers, MadGraph preparation and MARTY preparation;
* selection examples for HepMC conversion, bundle creation, cutflow execution,
  and trace-report generation;
* compact real-event samples chosen to illustrate representative selection
  outcomes while keeping the repository size under control.

Dash applications
-----------------

Two optional Dash applications are bundled in the repository:

* **SET-ANUBIS HepMC explorer** for event-by-event visual inspection in the
  ATLAS cavern / ANUBIS geometry;
* **SET-ANUBIS DB dashboard** for browsing stored runs, bundle sizes, storage
  savings and metadata consistency.

They are especially useful for validation, debugging and demonstrations, while
the documented Python API remains the primary route for scripted analyses.
