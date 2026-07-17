"""Build the deterministic selection bundle from the compact real-event CSV."""

from __future__ import annotations

import argparse
from importlib.resources import as_file, files
from pathlib import Path

import pandas as pd

from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer

from _common import ensure_output_dir, sha256_file, write_json


def run(output_dir: str | Path) -> dict:
    output = ensure_output_dir(output_dir)
    resource = files("SetAnubis.examples.Selection").joinpath(
        "InputFiles/hnl_selection_cutflow_df.csv.gz"
    )
    with as_file(resource) as input_path:
        dataframe = pd.read_csv(input_path)

    bundle = LLPAnalyzer(
        dataframe.copy(),
        pt_min_cfg={"chargedTrack": 5.0, "neutralTrack": 5.0, "jet": 15.0},
    ).create_sample_dataframes(9900012)

    llp_path = output / "selected_llps.csv"
    bundle["LLPs"].to_csv(llp_path, index=False)

    summary = {
        "input_rows": int(len(dataframe)),
        "input_events": int(dataframe["eventNumber"].nunique()),
        "llp_pdg": 9900012,
        "charged_track_pt_min_gev": 5.0,
        "bundle_rows": {name: int(len(frame)) for name, frame in sorted(bundle.items())},
        "selected_llp_events": int(bundle["LLPs"]["eventNumber"].nunique()),
        "selected_llps_sha256": sha256_file(llp_path),
    }
    write_json(output / "selection_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reproducibility_outputs/selection")
    args = parser.parse_args()
    print(run(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
