"""Prepare MadGraph cards for a width calculation without launching MadGraph."""

from __future__ import annotations

import argparse
from pathlib import Path

from SetAnubis import SetAnubisInterface, ufo_path
from SetAnubis.core.MadGraph.adapters.input.ParamCardBuilder import ParamCardBuilder
from SetAnubis.core.MadGraph.adapters.input.RunCardBuilder import RunCardBuilder
from SetAnubis.core.MadGraph.domain.MadGraphCommandCard import MadGraphCommandCard
from SetAnubis.core.MadGraph.domain.MadGraphCommandConfig import MadGraphCommandConfig


def prepare_madgraph_width_cards(output_dir: str | Path) -> dict[str, Path]:
    """Write command, run, and parameter cards for ``compute_widths n1``."""
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    model_path = ufo_path("UFO_HNL")
    model = SetAnubisInterface(str(model_path))

    command = MadGraphCommandCard(
        MadGraphCommandConfig(
            neo_set_anubis=model,
            cache=False,
            shower="",
            madspin="",
        )
    )
    command.add_process("compute_widths n1")
    command.set_output_launch("SETANUBIS_WIDTHS")
    command.configure_cards()

    run_card = RunCardBuilder()
    run_card.set("nevents", 1)
    run_card.set_random_seed(12345)

    payloads = {
        "madgraph_width_commands.txt": command.serialize(),
        "run_card.dat": run_card.serialize(),
        "param_card.dat": ParamCardBuilder(
            model_path / "write_param_card.py"
        ).serialize(),
    }
    paths: dict[str, Path] = {}
    for filename, payload in payloads.items():
        path = output / filename
        path.write_text(payload, encoding="utf-8")
        paths[filename] = path
    return paths


def main() -> int:
    """Generate MadGraph width inputs without starting MadGraph or Docker."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="madgraph_width_prepared")
    args = parser.parse_args()
    for name, path in prepare_madgraph_width_cards(args.output_dir).items():
        print(f"{name}: {path}")
    print("MadGraph and Docker were not launched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
