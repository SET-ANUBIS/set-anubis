from pathlib import Path
import yaml
from SetAnubis.core.MadGraph.adapters.input.GeneralCardInterface import GeneralCardInterface, MadGraphCommandConfig
from SetAnubis.core.MadGraph.adapters.input.MadGraphInterface import MadgraphDockerInterface

def run_madgraph(config_path, dry_run=True):
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    mg_config = MadGraphCommandConfig(
        ufo_path=Path(config["ufo_path"]),
        cards_path=Path(config["cards_path"]),
        cache=False,
        model_in_madgraph=config["model_in_madgraph"],
        shower=config.get("shower", "py8"),
        madspin=config.get("madspin", "ON")
    )

    card_interface = GeneralCardInterface(mg_config)

    # param_card
    param_card = card_interface.param_card

    # run_card
    run_card_builder = card_interface.run_card_builder
    run_card_builder.set("nevents", config.get("nevents", 2000))
    runcard_str = run_card_builder.serialize()

    # madspin
    madspin_builder = card_interface.madspin_builder
    for decay in config.get("decays", []):
        madspin_builder.add_decay(decay)
    madspin_str = madspin_builder.serialize()

    # pythia
    pythia_str = card_interface.pythia_card

    # job script
    jobcard = card_interface.josbscript_builder
    for proc in config.get("processes", []):
        jobcard.add_process(proc)
    jobcard.set_output_launch(config["output_name"])
    jobcard.configure_cards()

    for param, scan_range in config.get("parameter_scans", {}).items():
        jobcard.add_parameter_scan(param, scan_range)

    jobscript_str = jobcard.serialize()

    print("------------------------------------------------------------------------------------------")
    print("💼 JOBSCRIPT:\n", jobscript_str)
    print("------------------------------------------------------------------------------------------")
    print("🎯 MADSPIN:\n", madspin_str)
    print("------------------------------------------------------------------------------------------")
    print("🌀 PYTHIA:\n", pythia_str)
    print("------------------------------------------------------------------------------------------")
    print("📊 RUN CARD:\n", runcard_str)
    print("------------------------------------------------------------------------------------------")
    print("🧬 PARAM CARD:\n", param_card)
    print("------------------------------------------------------------------------------------------")

    if not dry_run:
        mg = MadgraphDockerInterface(
            jobscript_str=jobscript_str,
            param_card_str=param_card,
            run_card_str=runcard_str,
            pythia_card_str=pythia_str,
            madspin_card_str=madspin_str
        )
        mg.run()
        mg.retrieve_events()
