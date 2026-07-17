Program overview
================

SET-ANUBIS was developed to perform ANUBIS sensitivity studies for different
BSM scenarios without rebuilding the complete analysis for every model. The
model-dependent information is introduced at the beginning of the workflow,
whereas event representation, detector geometry, selection and provenance are
shared.

Scientific workflow
-------------------

A complete analysis can be divided into three connected tasks.

Signal-sample preparation
~~~~~~~~~~~~~~~~~~~~~~~~~

A UFO model provides particles, parameters and interactions. The relevant scan
parameters are set through the model interface, and the corresponding widths,
branching ratios and lifetimes are obtained from one of the supported
calculation strategies. SET-ANUBIS then prepares generator inputs for MadGraph
or, where appropriate, an optional Pythia workflow. Generated samples are
expected to be available in HepMC format before detector acceptance is
evaluated.

Geometric acceptance and event selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

HepMC events are converted into dataframe-based analysis objects. LLP decay
vertices and charged decay products are propagated through a model of the ATLAS
cavern, ATLAS exclusion volume, service shafts and ANUBIS RPC stations. The
selection first evaluates whether a decay is geometrically observable and then
applies missing-transverse-momentum and isolation requirements associated with
the accompanying ATLAS event.

Sensitivity inputs and provenance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The selected fraction provides the acceptance for the specified model point,
geometry and cut configuration. It can be combined with luminosity, production
cross section, branching fraction and signal efficiency to estimate an expected
event yield. Generator cards, scan parameters, event metadata and compact
selection-ready bundles can be stored in an SQLite catalogue and a
content-addressed store so that the analysis inputs remain auditable.

Software architecture
---------------------

The framework follows a ports-and-adapters design. Each domain defines a small
interface describing the required behaviour; adapters implement file I/O,
database access, external programs and visualisation. This organisation serves a
scientific purpose rather than only a software-engineering one:

* physics logic can be tested independently of large external toolchains;
* alternative width calculators or generators can be compared through the same
  domain interface;
* model scans share one geometry and selection implementation;
* provenance and validation are not tied to a single execution environment.

Main domains
------------

``ModelCore`` and UFO interface
   Load the model, expose particle content and parameters, and generate
   parameter-card information.

``BranchingRatio``
   Evaluate partial and total widths, branching ratios and lifetimes from
   explicit values, Python functions, interpolation tables, UFO information,
   MadGraph preparation or MARTY preparation.

``MadGraph`` and ``Pythia``
   Prepare event-generation inputs. MadGraph is the principal documented
   campaign workflow; Pythia command generation and an optional native binding
   are available for dedicated studies and cross-checks.

``Geometry`` and ``Selection``
   Construct the cavern and ANUBIS station geometry, transform HepMC events into
   analysis objects, and apply the ordered acceptance and selection criteria.

``DataBase``
   Relate model points, cards, banners, event samples and compact dataframe
   bundles. Large artefacts can be addressed by content while the SQL catalogue
   retains queryable metadata.

Validation examples
-------------------

The examples are part of the scientific validation of the release. They include
small, deterministic workflows for every main domain and a compact sample of
seven real HNL events. The selected events illustrate the observed stopping
points of the nominal cutflow while keeping the distributed data below 1 MB.
