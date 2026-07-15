"""Build the deterministic selection data bundle from the bundled HNL CSV."""

from __future__ import annotations

import argparse
from importlib.resources import files
from pathlib import Path

import pandas as pd

from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer

from _common import ensure_output_dir, sha256_file, write_json


def run(output_dir: str | Path) -> dict:
    output = ensure_output_dir(output_dir)
    input_path = files("SetAnubis.examples.Selection").joinpath("InputFiles/hnl_df.csv")
    dataframe = pd.read_csv(input_path)

    bundle = LLPAnalyzer(
        dataframe.copy(),
        pt_min_cfg={"chargedTrack": 0.5},
    ).create_sample_dataframes(9900012)

    llp_path = output / "selected_llps.csv"
    bundle["LLPs"].to_csv(llp_path, index=False)

    summary = {
        "input_rows": int(len(dataframe)),
        "input_events": int(dataframe["eventNumber"].nunique()),
        "llp_pdg": 9900012,
        "charged_track_pt_min_gev": 0.5,
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
