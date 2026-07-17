MadGraph signal generation
==========================

MadGraph is the primary generation workflow documented for the release.  In a
SET-ANUBIS analysis the generator stage is responsible for producing a sample of
LLP events for a given model and parameter point.  The subsequent selection code
assumes that generated events can be converted to HepMC/dataframe bundles, but it
is deliberately agnostic about the exact generator backend once the event record
exists.

Physics role
------------

For HNL-like benchmarks the relevant information is split between:

* the UFO model, which defines particles, parameters and interactions;
* the MadGraph process definition, such as associated HNL production;
* the parameter card, where masses, mixings and widths are set or scanned;
* the run card, where collider conditions and event counts are configured;
* the MadSpin card, which defines LLP decays at the parton level;
* the shower card, which controls the optional shower/hadronisation step.

SET-ANUBIS keeps these text artefacts explicit because they are part of the
scientific provenance of a scan.  They can be written, inspected, stored in the
database and later associated with selection outputs.

HNL card-generation example
---------------------------

The example below constructs cards for a simple Heavy Neutral Lepton scan.  It is
a dry-run card construction example: no MadGraph process is launched until the
strings are handed to a local or Docker runner.

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

The output layout expected by the database layer follows the standard MadGraph
convention:

.. code-block:: text

   <campaign>/
     Events/
       run_01/
         tag_1_pythia8_events.hepmc.gz
         run_01_tag_1_banner.txt
       run_01_decayed_1/
         tag_1_pythia8_events.hepmc.gz
     scan_run_01.txt

Running MadGraph
----------------

The public examples keep execution separate from card construction because
production campaigns may run locally, inside Docker, or on a batch system.  Once
the cards have been created, use the appropriate runner for your environment:

.. code-block:: python

   from setanubis import MadgraphInterface, MadGraphDockerRunner

   runner = MadGraphDockerRunner()
   mg = MadgraphInterface(
       madgraph_runner=runner,
       jobscript_str=jobscript,
       param_card_str=param_card,
       run_card_str=run_card,
       pythia_card_str=pythia_card,
       madspin_card_str=madspin_card,
   )
   mg.run()
   mg.retrieve_events("db/Temp/madgraph/Events")

Recommended examples
--------------------

* ``setanubis/SetAnubis/examples/MadGraph/example_madgraph_interface.py``
* ``setanubis/SetAnubis/examples/MadGraph/example_run_card.py``
* ``setanubis/SetAnubis/examples/MadGraph/example_madspin_card.py``
* ``setanubis/SetAnubis/examples/MadGraph/example_hepmc_plots.py``

  Run it with an explicit HepMC input, for example::

     python -m SetAnubis.examples.MadGraph.example_hepmc_plots path/to/events.hepmc.gz --pdg-id 35
