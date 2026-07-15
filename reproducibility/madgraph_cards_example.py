"""Create deterministic MadGraph cards without launching MadGraph or Docker."""

from __future__ import annotations

import argparse
from pathlib import Path

from SetAnubis import ufo_path
from SetAnubis.core.MadGraph.adapters.input.MadspinCardBuilder import MadSpinCardAdapter
from SetAnubis.core.MadGraph.adapters.input.ParamCardBuilder import ParamCardBuilder
from SetAnubis.core.MadGraph.adapters.input.PythiaCardBuilder import PythiaCardBuilder
from SetAnubis.core.MadGraph.adapters.input.RunCardBuilder import RunCardBuilder
from SetAnubis.core.MadGraph.domain.MadGraphCommandCard import MadGraphCommandCard
from SetAnubis.core.MadGraph.domain.MadGraphCommandConfig import MadGraphCommandConfig
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface

from _common import ensure_output_dir, sha256_file, write_json


def run(output_dir: str | Path) -> dict:
    output = ensure_output_dir(output_dir)
    model = SetAnubisInterface(ufo_path("UFO_HNL"))

    run_card = RunCardBuilder()
    run_card.set("nevents", 100)
    run_card.set_random_seed(12345)

    madspin_card = MadSpinCardAdapter()
    madspin_card.clear_decays()
    madspin_card.add_decay("decay n1 > e+ e- ve")

    command_config = MadGraphCommandConfig(
        neo_set_anubis=model,
        cache=False,
        shower="py8",
        madspin="ON",
    )
    command_card = MadGraphCommandCard(command_config)
    command_card.add_process("generate p p > n1 ve")
    command_card.set_output_launch("SETANUBIS_HNL")
    command_card.configure_cards()

    cards = {
        "run_card.dat": run_card.serialize(),
        "param_card.dat": ParamCardBuilder(ufo_path("UFO_HNL") / "write_param_card.py").serialize(),
        "pythia8_card.dat": PythiaCardBuilder().serialize(),
        "madspin_card.dat": madspin_card.serialize(),
        "madgraph_commands.txt": command_card.serialize(),
    }

    hashes = {}
    for filename, text in cards.items():
        path = output / filename
        path.write_text(text, encoding="utf-8")
        hashes[filename] = sha256_file(path)

    summary = {
        "model": "UFO_HNL",
        "nevents": 100,
        "random_seed": 12345,
        "process": "generate p p > n1 ve",
        "cards": hashes,
        "madgraph_executed": False,
        "docker_executed": False,
    }
    write_json(output / "madgraph_cards_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reproducibility_outputs/madgraph")
    args = parser.parse_args()
    print(run(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
