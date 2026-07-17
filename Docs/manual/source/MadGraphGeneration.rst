MadGraph signal generation
==========================

MadGraph is the principal event-generation workflow documented for the public
release. For each model point, SET-ANUBIS constructs the text inputs that define
the hard process, collider configuration, model parameters, LLP decay chain and
optional shower stage. Keeping these inputs explicit is essential: the cards are
part of the scientific definition of the generated sample and therefore part of
its provenance.

Role of the generator stage
---------------------------

For an HNL-like benchmark, the generated sample is determined by several linked
inputs:

* the UFO model, which specifies particles, parameters and interactions;
* the process definition, which selects the production mode;
* the parameter card, which fixes or scans masses, mixings and widths;
* the run card, which defines beam conditions, statistics and generator options;
* the MadSpin card, which specifies parton-level decay chains;
* the shower card, which configures optional showering and hadronisation.

SET-ANUBIS separates card construction from execution. The same card strings can
be inspected locally, stored in the event database, submitted to a local
MadGraph installation, executed in a Docker container or passed to a batch
system.

HNL card-generation example
---------------------------

The example below prepares an associated-production scan without launching
MadGraph.

.. code-block:: python

   from setanubis import (
       SetAnubisInterface,
       MadGraphCommandConfig,
       GeneralCardInterface,
       ufo_path,
   )

   model = SetAnubisInterface(str(ufo_path("UFO_HNL")))

   config = MadGraphCommandConfig(
       neo_set_anubis=model,
       model_in_madgraph="UFO_HNL",
       shower="py8",
       madspin="ON",
       cache=False,
   )

   cards = GeneralCardInterface(config)
   cards.run_card_builder.set("nevents", 2000)
   cards.run_card_builder.set("ebeam1", 6800)
   cards.run_card_builder.set("ebeam2", 6800)

   cards.madspin_builder.clear_decays()
   cards.madspin_builder.add_decay("decay n1 > ell ell vv")

   job = cards.jobscript_builder
   job.add_process("generate p p > n1 ell # [QCD]")
   job.set_output_launch("HNL_ANUBIS_scan")
   job.configure_cards()
   job.add_parameter_scan("MN1", "[0.5, 1.0, 2.0]")
   job.add_parameter_scan("VeN1", "[1e-6, 1e-5]")

   jobscript = job.serialize()
   run_card = cards.run_card_builder.serialize()
   param_card = cards.param_card
   madspin_card = cards.madspin_builder.serialize()
   pythia_card = cards.pythia_builder.serialize()

Run layout and ingestion
------------------------

The database importer understands the conventional MadGraph ``Events`` layout
and scan summaries:

.. code-block:: text

   <campaign>/
     Events/
       run_01/
         tag_1_pythia8_events.hepmc.gz
         run_01_tag_1_banner.txt
       run_01_decayed_1/
         tag_1_pythia8_events.hepmc.gz
     scan_run_01.txt

Cards, banners, scan parameters, cross sections and event references can then be
associated with a single model point. The persistent analysis object is normally
a compact selection-ready dataframe bundle; retaining the raw HepMC file remains
an explicit option for benchmark or archival runs.

Execution backends
------------------

Once the card strings have been prepared, the corresponding runner can be
selected for the target environment:

.. code-block:: python

   from setanubis import MadgraphInterface, MadGraphDockerRunner

   runner = MadGraphDockerRunner()
   interface = MadgraphInterface(
       madgraph_runner=runner,
       jobscript_str=jobscript,
       param_card_str=param_card,
       run_card_str=run_card,
       pythia_card_str=pythia_card,
       madspin_card_str=madspin_card,
   )
   interface.run()
   interface.retrieve_events("db/Temp/madgraph/Events")

The Docker backend isolates the generator toolchain from the Python environment.
For publication-quality production, record the image digest, generator version,
cards, random seeds and host information together with the campaign metadata.

Recommended examples
--------------------

* ``setanubis/SetAnubis/examples/MadGraph/example_madgraph_interface.py``
* ``setanubis/SetAnubis/examples/MadGraph/example_run_card.py``
* ``setanubis/SetAnubis/examples/MadGraph/example_madspin_card.py``
* ``setanubis/SetAnubis/examples/MadGraph/example_hepmc_plots.py``

The plotting example accepts an explicit HepMC file:

.. code-block:: bash

   python -m SetAnubis.examples.MadGraph.example_hepmc_plots \
      path/to/events.hepmc.gz --pdg-id 35
