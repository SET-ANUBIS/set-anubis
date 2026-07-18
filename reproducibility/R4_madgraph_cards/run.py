"""R4: generate deterministic MadGraph-related cards without external execution."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SOURCE_ROOT = REPOSITORY_ROOT / "setanubis"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from setanubis import SetAnubisInterface, ufo_path
from SetAnubis.core.MadGraph.adapters.input.MadspinCardBuilder import MadSpinCardAdapter
from SetAnubis.core.MadGraph.adapters.input.ParamCardBuilder import ParamCardBuilder
from SetAnubis.core.MadGraph.adapters.input.PythiaCardBuilder import PythiaCardBuilder
from SetAnubis.core.MadGraph.adapters.input.RunCardBuilder import RunCardBuilder
from SetAnubis.core.MadGraph.domain.MadGraphCommandCard import MadGraphCommandCard
from SetAnubis.core.MadGraph.domain.MadGraphCommandConfig import MadGraphCommandConfig

from reproducibility._common import (
    ensure_clean_output_dir,
    read_json,
    sha256_file,
    write_json,
)

HERE = Path(__file__).resolve().parent


def run(output_dir: str | Path = HERE / "output") -> dict:
    """Write all generator input cards and return their SHA-256 identifiers."""
    config = read_json(HERE / "input/config.json")
    output = ensure_clean_output_dir(output_dir)
    model_path = ufo_path(config["model"])
    model = SetAnubisInterface(model_path)

    run_card = RunCardBuilder()
    run_card.set("nevents", int(config["nevents"]))
    run_card.set_random_seed(int(config["random_seed"]))

    madspin_card = MadSpinCardAdapter()
    madspin_card.clear_decays()
    madspin_card.add_decay(config["decay"])

    command_card = MadGraphCommandCard(
        MadGraphCommandConfig(
            neo_set_anubis=model,
            cache=False,
            shower=config["shower"],
            madspin=config["madspin"],
        )
    )
    command_card.add_process(config["process"])
    command_card.set_output_launch(config["output_name"])
    command_card.configure_cards()

    cards = {
        "run_card.dat": run_card.serialize(),
        "param_card.dat": ParamCardBuilder(model_path / "write_param_card.py").serialize(),
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
        "scenario": "R4_madgraph_cards",
        "model": config["model"],
        "process": config["process"],
        "nevents": int(config["nevents"]),
        "random_seed": int(config["random_seed"]),
        "cards": hashes,
        "madgraph_executed": False,
        "docker_executed": False,
    }
    write_json(output / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(HERE / "output"))
    args = parser.parse_args()
    print(run(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
