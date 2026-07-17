"""Build all MadGraph cards in memory and optionally launch the Docker runner."""

from SetAnubis.core.MadGraph.adapters.input.GeneralCardInterface import (
    GeneralCardInterface,
    MadGraphCommandConfig,
)
from SetAnubis.core.MadGraph.adapters.input.MadGraphInterface import MadgraphInterface
from SetAnubis.core.interfaces import SetAnubisInterface
from SetAnubis.resources import ufo_path


if __name__ == "__main__":
    # Keep this True to inspect generated cards without requiring Docker/MadGraph.
    dry_run = True

    # The model interface supplies UFO parameters to all card builders.
    model = SetAnubisInterface(ufo_path("UFO_HNL"))
    config = MadGraphCommandConfig(
        neo_set_anubis=model,
        cache=False,
        model_in_madgraph="SM_HeavyN_CKM_AllMasses_LO",
        shower="py8",
        madspin="ON",
    )
    cards = GeneralCardInterface(config)

    # Customize each card through its dedicated builder before serialization.
    param_card = cards.param_card
    cards.run_card_builder.set("nevents", 2000)
    run_card = cards.run_card_builder.serialize()

    cards.madspin_builder.add_decay("decay n1 > ell ell vv")
    madspin_card = cards.madspin_builder.serialize()
    pythia_card = cards.pythia_builder.serialize()

    job_card = cards.jobscript_builder
    job_card.add_process("generate p p > n1 ell # [QCD]")
    job_card.set_output_launch("HNL_Condor_CCDY_qqe")
    job_card.configure_cards()
    job_card.add_parameter_scan("VeN1", "[1e-6, 1.]")
    job_card.add_parameter_scan("MN1", "[0.5, 1.0]")
    job_script = job_card.serialize()

    for title, content in (
        ("job card", job_script),
        ("MadSpin card", madspin_card),
        ("Pythia card", pythia_card),
        ("run card", run_card),
        ("param card", param_card),
    ):
        print(f"--- {title} ---")
        print(content)

    if not dry_run:
        # Import Docker support only when the external execution is requested.
        from SetAnubis.core.MadGraph.adapters.output.MadGraphDockerRunner import (
            MadGraphDockerRunner,
        )

        interface = MadgraphInterface(
            madgraph_runner=MadGraphDockerRunner(),
            jobscript_str=job_script,
            param_card_str=param_card,
            run_card_str=run_card,
            pythia_card_str=pythia_card,
            madspin_card_str=madspin_card,
        )
        interface.run()
        interface.retrieve_events()
