"""R5: rebuild the compact sample from HepMC and reproduce the selection cutflow."""

from __future__ import annotations

import argparse
from importlib.resources import as_file, files
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SOURCE_ROOT = REPOSITORY_ROOT / "setanubis"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from setanubis import SetAnubisInterface, ufo_path
from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource
from SetAnubis.core.Selection.domain.HepMCFrameBuilder import (
    HepmcFrameBuilder,
    HepmcFrameOptions,
)
from SetAnubis.core.Selection.domain.SelectionEngine import RunConfig
from SetAnubis.examples.Selection.compact_sample import (
    build_selection_config,
    build_selection_pipeline,
)

from reproducibility._common import ensure_clean_output_dir, read_json, write_json

HERE = Path(__file__).resolve().parent


def _resource(specification: str):
    package, relative = specification.split(":", 1)
    return files(package).joinpath(relative)


def run(output_dir: str | Path = HERE / "output") -> dict:
    """Convert the packaged HepMC source, run the cutflow, and write trace reports."""
    try:
        import pyhepmc
    except ImportError as exc:  # pragma: no cover - documented optional dependency
        raise RuntimeError("R5 requires SetAnubis[selection] (pyhepmc).") from exc

    config = read_json(HERE / "input/config.json")
    output = ensure_clean_output_dir(output_dir)
    builder = HepmcFrameBuilder(
        neo_manager=SetAnubisInterface(ufo_path(config["model"])),
        options=HepmcFrameOptions(progress_every=None, compute_met=False),
    )
    with as_file(_resource(config["hepmc_resource"])) as hepmc_path:
        with pyhepmc.open(hepmc_path) as stream:
            dataframe, unknown_pids = builder.build_from_events(stream)

    dataframe_path = output / "events_from_hepmc.csv.gz"
    dataframe.to_csv(
        dataframe_path,
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    result = build_selection_pipeline().run(
        EventsBundleSource.from_events_dataframe(dataframe),
        build_selection_config(),
        RunConfig(capture_intermediate=bool(config["capture_intermediate"])),
    )
    trace = result["trace"]
    trace.write_report(
        output,
        basename="selection_trace",
        title="SET-ANUBIS CPC reproducibility selection trace",
    )

    cutflow = result["cutFlow"]
    stage_keys = [
        "nLLP_original",
        "nLLP_LLPdecay",
        "nLLP_InCavern",
        "nLLP_NotInATLAS",
        "nLLP_Geometry",
        "nLLP_Tracker",
        "nLLP_MET",
        "nLLP_IsoJet",
        "nLLP_IsoCharged",
        "nLLP_IsoAll",
        "nLLP_Final",
    ]
    outcomes = [
        {
            "event_number": int(row["eventNumber"]),
            "last_passed_stage": str(row["last_passed_stage"]),
        }
        for row in trace.event_summary.to_dict(orient="records")
    ]
    summary = {
        "scenario": "R5_selection",
        "source_format": "HepMC2 gzip",
        "input_events": int(dataframe["eventNumber"].nunique()),
        "input_rows": int(len(dataframe)),
        "unknown_pdg_ids": sorted(int(pid) for pid in unknown_pids),
        "llp_pdg": int(config["llp_pdg"]),
        "cutflow_counts": {key: int(cutflow[key]) for key in stage_keys},
        "event_outcomes": outcomes,
        "final_event_numbers": sorted(
            int(value) for value in result["finalDF"]["eventNumber"].unique()
        ),
        "reports": ["selection_trace.json", "selection_trace.html"],
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
