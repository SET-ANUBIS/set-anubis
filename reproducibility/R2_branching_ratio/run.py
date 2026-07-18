"""R2: reproduce partial widths, total width, BRs and lifetime inputs."""

from __future__ import annotations

import argparse
from importlib.resources import files
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SOURCE_ROOT = REPOSITORY_ROOT / "setanubis"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from setanubis import (
    CalculationDecayStrategy,
    DecayInterface,
    SetAnubisInterface,
    ufo_path,
)

from reproducibility._common import ensure_clean_output_dir, read_json, write_json

HERE = Path(__file__).resolve().parent


def _resource_path(specification: str) -> str:
    package, relative = specification.split(":", 1)
    return str(files(package).joinpath(relative))


def run(output_dir: str | Path = HERE / "output") -> dict:
    """Evaluate the version-controlled interpolation table and write a summary."""
    config = read_json(HERE / "input/config.json")
    output = ensure_clean_output_dir(output_dir)
    model = SetAnubisInterface(ufo_path(config["model"]))
    for name, value in config["parameters"].items():
        model.set_leaf_param(name, float(value))

    channels = config["channels"]
    decays = DecayInterface(model)
    decays.add_decays(
        [
            {"mother": config["mother_pdg"], "daughters": daughters}
            for daughters in channels.values()
        ],
        CalculationDecayStrategy.FILE_INTERPOLATION,
        {
            "file_path": _resource_path(config["table_resource"]),
            "varying_params": list(config["parameters"]),
            "format_type": "csv",
        },
    )
    mother = int(config["mother_pdg"])
    partial_widths = {
        name: float(decays.get_decay(mother, daughters))
        for name, daughters in channels.items()
    }
    branching_ratios = {
        name: float(decays.get_br(mother, daughters))
        for name, daughters in channels.items()
    }
    summary = {
        "scenario": "R2_branching_ratio",
        "model": config["model"],
        "mother_pdg": mother,
        "parameters": config["parameters"],
        "partial_widths_gev": partial_widths,
        "total_width_gev": float(decays.get_decay_tot(mother)),
        "branching_ratios": branching_ratios,
        "calculation_backend": "file_interpolation",
        "external_calculator_executed": False,
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
