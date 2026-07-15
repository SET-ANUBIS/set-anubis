"""Reproduce branching ratios without invoking MARTY."""

from __future__ import annotations

import argparse
from importlib.resources import files
from pathlib import Path

from SetAnubis import ufo_path
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import (
    CalculationDecayStrategy,
    DecayInterface,
)
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface

from _common import ensure_output_dir, write_json


def run(output_dir: str | Path) -> dict:
    output = ensure_output_dir(output_dir)
    model = SetAnubisInterface(ufo_path("UFO_HNL"))
    model.set_leaf_param("mN1", 1.0)
    model.set_leaf_param("VeN1", 1.0)

    csv_path = files("SetAnubis.examples.BranchingRatio").joinpath("TestFiles/test_BR.csv")
    decays = DecayInterface(model)
    decays.add_decays(
        [
            {"mother": 25, "daughters": [-13, 13]},
            {"mother": 25, "daughters": [22, 22]},
        ],
        CalculationDecayStrategy.FILE_INTERPOLATION,
        {
            "file_path": str(csv_path),
            "varying_params": ["mN1", "VeN1"],
            "format_type": "csv",
        },
    )

    summary = {
        "mother_pdg": 25,
        "parameters": {"mN1": 1.0, "VeN1": 1.0},
        "partial_widths": {
            "H_to_mu_mu": float(decays.get_decay(25, [-13, 13])),
            "H_to_gamma_gamma": float(decays.get_decay(25, [22, 22])),
        },
        "total_width": float(decays.get_decay_tot(25)),
        "branching_ratios": {
            "H_to_mu_mu": float(decays.get_br(25, [-13, 13])),
            "H_to_gamma_gamma": float(decays.get_br(25, [22, 22])),
        },
        "calculation_backend": "file_interpolation",
        "marty_executed": False,
    }
    write_json(output / "branching_ratio_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reproducibility_outputs/branching_ratio")
    args = parser.parse_args()
    print(run(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
