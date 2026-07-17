"""Regenerate the compact flat selection dataframe from its HepMC2 source."""

from __future__ import annotations

import argparse
from importlib.resources import as_file
from pathlib import Path

from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.Selection.domain.HepMCFrameBuilder import (
    HepmcFrameBuilder,
    HepmcFrameOptions,
)
from SetAnubis.examples.Selection.compact_sample import compact_hepmc_resource
from SetAnubis.resources import ufo_path


def convert(output: str | Path) -> Path:
    """Convert the seven packaged events and return the generated CSV path."""
    try:
        import pyhepmc
    except ImportError as exc:  # pragma: no cover - optional dependency path
        raise SystemExit("Install SetAnubis[selection] to read HepMC files.") from exc

    builder = HepmcFrameBuilder(
        neo_manager=SetAnubisInterface(ufo_path("UFO_HNL")),
        options=HepmcFrameOptions(progress_every=None, compute_met=False),
    )
    with as_file(compact_hepmc_resource()) as hepmc_path:
        with pyhepmc.open(hepmc_path) as stream:
            dataframe, unknown_pids = builder.build_from_events(stream)
    if unknown_pids:
        print(f"Unknown PDG IDs were assigned a null charge: {unknown_pids}")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False, compression="infer")
    return output_path


def main() -> None:
    """Parse the output filename and regenerate the compact dataframe."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="hnl_selection_cutflow_df.csv.gz",
        help="Destination CSV or CSV.GZ path.",
    )
    args = parser.parse_args()
    print(f"Saved dataframe to {convert(args.output).resolve()}")


if __name__ == "__main__":
    main()
