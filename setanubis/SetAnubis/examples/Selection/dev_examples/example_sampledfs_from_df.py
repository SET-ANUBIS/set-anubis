"""Regenerate the reusable selection bundle from the compact real-event CSV."""

from __future__ import annotations

from SetAnubis.examples._runtime import run_example_entrypoint

import argparse
from pathlib import Path

from SetAnubis.core.Selection.domain.DatasetSource import BundleIO
from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer
from SetAnubis.examples.Selection.compact_sample import load_compact_dataframe


def build_bundle(output: str | Path) -> Path:
    """Build and save the trusted gzip-pickle dataframe bundle."""
    dataframe = load_compact_dataframe()
    bundle = LLPAnalyzer(
        dataframe.copy(),
        pt_min_cfg={"chargedTrack": 5.0, "neutralTrack": 5.0, "jet": 15.0},
    ).create_sample_dataframes(llpid=9900012)
    output_path = Path(output)
    BundleIO.save_bundle(bundle, output_path)
    return output_path


def main() -> None:
    """Parse the output filename and write the generated bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="hnl_selection_cutflow_bundle.pkl.gz",
        help="Destination trusted pickle bundle.",
    )
    args = parser.parse_args()
    print(f"Saved bundle to {build_bundle(args.output).resolve()}")


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
