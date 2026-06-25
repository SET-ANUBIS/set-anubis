"""Small YAML-driven MadGraph card-generation helper.

This module is intentionally dry-run first: it builds and prints the cards by
default, and only runs MadGraph when ``dry_run=False`` is passed by a caller.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from SetAnubis.core.interfaces import SetAnubisInterface
from SetAnubis.core.MadGraph.adapters.input.GeneralCardInterface import GeneralCardInterface
from SetAnubis.core.MadGraph.adapters.input.MadGraphInterface import MadgraphInterface
from SetAnubis.core.MadGraph.adapters.output.MadGraphDockerRunner import MadGraphDockerRunner
from SetAnubis.core.MadGraph.domain.MadGraphCommandConfig import MadGraphCommandConfig


def run_madgraph(config_path: str | Path, dry_run: bool = True) -> dict[str, Any]:
    """Build MadGraph cards from a compact YAML configuration.

    Expected keys include ``ufo_path``, ``model_in_madgraph``, ``output_name``,
    ``processes``, ``decays`` and ``parameter_scans``.  The function returns the
    generated card strings so it can be unit-tested without Docker/MadGraph.
    """
    with Path(config_path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    model = SetAnubisInterface(str(Path(config["ufo_path"])))
    mg_config = MadGraphCommandConfig(
        neo_set_anubis=model,
        cache=bool(config.get("cache", False)),
        model_in_madgraph=config.get("model_in_madgraph", Path(config["ufo_path"]).name),
        shower=config.get("shower", "py8"),
        madspin=config.get("madspin", "ON"),
    )

    cards = GeneralCardInterface(mg_config)
    cards.run_card_builder.set("nevents", config.get("nevents", 2000))

    cards.madspin_builder.clear_decays()
    for decay in config.get("decays", []):
        cards.madspin_builder.add_decay(decay)

    job = cards.jobscript_builder
    for process in config.get("processes", []):
        job.add_process(process)
    job.set_output_launch(config["output_name"])
    job.configure_cards()
    for parameter, scan_range in config.get("parameter_scans", {}).items():
        job.add_parameter_scan(parameter, scan_range)

    generated = {
        "jobscript": job.serialize(),
        "madspin": cards.madspin_builder.serialize(),
        "pythia": cards.pythia_builder.serialize(),
        "run_card": cards.run_card_builder.serialize(),
        "param_card": cards.param_card,
    }

    for title, content in generated.items():
        print("-" * 90)
        print(f"{title.upper()}:\n{content}")

    if not dry_run:
        runner = MadGraphDockerRunner()
        mg = MadgraphInterface(
            madgraph_runner=runner,
            jobscript_str=generated["jobscript"],
            param_card_str=generated["param_card"],
            run_card_str=generated["run_card"],
            pythia_card_str=generated["pythia"],
            madspin_card_str=generated["madspin"],
        )
        mg.run()
        mg.retrieve_events(config.get("events_output", "db/Temp/madgraph/Events"))

    return generated
