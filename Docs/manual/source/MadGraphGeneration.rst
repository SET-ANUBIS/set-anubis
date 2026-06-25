MadGraph generation workflow
============================

MadGraph is the primary release-path example for SET-ANUBIS generation studies.
The framework builds the text artefacts needed by MadGraph5_aMC@NLO campaigns:
job scripts, parameter cards, run cards, MadSpin cards and Pythia shower cards.
Those artefacts can then be run through the Docker/local adapters or submitted to
a batch system such as HTCondor.

The expected output layout follows the usual MadGraph convention:

.. code-block:: text

   <output directory>/
     Events/
       run_01/
         tag_1_pythia8_events.hepmc.gz
         run_01_tag_1_banner.txt
       run_02/
         ...
     scan_run_01.txt

Minimal card-generation example
-------------------------------

.. code-block:: python

   from setanubis import SetAnubisInterface, MadGraphCommandConfig, GeneralCardInterface, ufo_path

   model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
   config = MadGraphCommandConfig(
       neo_set_anubis=model,
       model_in_madgraph="SM_HeavyN_CKM_AllMasses_LO",
       shower="py8",
       madspin="ON",
       cache=False,
   )

   cards = GeneralCardInterface(config)
   cards.run_card_builder.set("nevents", 2000)

   cards.madspin_builder.clear_decays()
   cards.madspin_builder.add_decay("decay n1 > ell ell vv")

   job = cards.jobscript_builder
   job.add_process("generate p p > n1 ell # [QCD]")
   job.set_output_launch("HNL_scan_demo")
   job.configure_cards()
   job.add_parameter_scan("MN1", "[0.5, 1.0, 2.0]")
   job.add_parameter_scan("VeN1", "[1e-6, 1e-5]")

   jobscript = job.serialize()
   run_card = cards.run_card_builder.serialize()
   param_card = cards.param_card
   madspin_card = cards.madspin_builder.serialize()
   pythia_card = cards.pythia_builder.serialize()

Execution policy
----------------

The public examples default to dry-run card construction because production
campaigns usually run on Docker, a local MadGraph installation or a batch system.
When the execution backend is available, the same strings can be passed to
``MadGraphInterface`` with either ``MadGraphDockerRunner`` or
``MadGraphLocalRunner``.

Recommended examples
--------------------

* ``setanubis/SetAnubis/examples/MadGraph/example_madgraph_interface.py``
* ``setanubis/SetAnubis/examples/MadGraph/example_run_card.py``
* ``setanubis/SetAnubis/examples/MadGraph/example_madspin_card.py``
* ``setanubis/SetAnubis/examples/MadGraph/example_hepmc_plots.py``
