"""Reproduce a lightweight ModelCore/UFO inspection."""

from __future__ import annotations

import argparse
from pathlib import Path

from SetAnubis import __version__, ufo_path
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface

from _common import ensure_output_dir, write_json


def run(output_dir: str | Path) -> dict:
    output = ensure_output_dir(output_dir)
    model = SetAnubisInterface(ufo_path("UFO_HNL"))

    initial_hnl_mass = float(model.get_particle_mass(9900012))
    model.set_leaf_param("mN1", 1.0)

    summary = {
        "setanubis_version": __version__,
        "model": "UFO_HNL",
        "parameter_count": len(model.get_all_parameters()),
        "particle_count": len(model.get_all_particles()),
        "z_mass_gev": float(model.get_particle_mass(23)),
        "hnl_mass_initial_gev": initial_hnl_mass,
        "hnl_mass_updated_gev": float(model.get_particle_mass(9900012)),
        "hnl_name": model.get_particle_info(9900012)["name"],
    }
    write_json(output / "core_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reproducibility_outputs/core")
    args = parser.parse_args()
    print(run(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
