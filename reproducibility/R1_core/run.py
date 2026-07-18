"""R1: validate the public model interface and bundled HNL UFO."""

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

from setanubis import SetAnubisInterface, __version__, ufo_path

from reproducibility._common import ensure_clean_output_dir, read_json, write_json

HERE = Path(__file__).resolve().parent


def run(output_dir: str | Path = HERE / "output") -> dict:
    """Run the model-interface scenario and return its deterministic summary."""
    config = read_json(HERE / "input/config.json")
    output = ensure_clean_output_dir(output_dir)
    model = SetAnubisInterface(ufo_path(config["model"]))
    particle_pdg = int(config["particle_pdg"])
    reference_pdg = int(config["reference_particle_pdg"])
    initial_mass = float(model.get_particle_mass(particle_pdg))
    model.set_leaf_param(config["parameter"], float(config["updated_value_gev"]))

    summary = {
        "scenario": "R1_core",
        "setanubis_version": __version__,
        "model": config["model"],
        "parameter_count": len(model.get_all_parameters()),
        "particle_count": len(model.get_all_particles()),
        "reference_mass_gev": float(model.get_particle_mass(reference_pdg)),
        "llp_mass_initial_gev": initial_mass,
        "llp_mass_updated_gev": float(model.get_particle_mass(particle_pdg)),
        "llp_name": model.get_particle_info(particle_pdg)["name"],
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
