"""Add prompt jets and isolation distances to the compact real HNL sample."""

from __future__ import annotations

from SetAnubis.examples._runtime import run_example_entrypoint

import argparse
from pathlib import Path

import numpy as np

from SetAnubis.core.Selection.domain.DatasetSource import BundleIO
from SetAnubis.core.Selection.domain.JetBuilder import createJetDF
from SetAnubis.core.Selection.domain.isolation import IsolationComputer
from SetAnubis.examples.Selection.compact_sample import (
    build_selection_config,
    load_compact_bundle,
)


def enrich_bundle(output: str | Path) -> Path:
    """Cluster jets, attach isolation values, and save the enriched bundle."""
    sample_dfs = load_compact_bundle()
    charged = sample_dfs["chargedFinalStates"].copy()
    neutral = sample_dfs["neutralFinalStates"].copy()

    # Build prompt jets from all visible prompt final-state particles.
    event_numbers = np.unique(
        np.concatenate(
            [
                charged["eventNumber"].to_numpy(dtype=int, copy=False),
                neutral["eventNumber"].to_numpy(dtype=int, copy=False),
            ]
        )
    )
    enriched_bundle = sample_dfs.copy()
    enriched_bundle["finalStatePromptJets"] = createJetDF(
        event_numbers,
        charged,
        neutral,
    )

    # Attach the minimum angular distance to jets and charged tracks per LLP.
    isolation = IsolationComputer(selection=build_selection_config())
    enriched_bundle["LLPs"] = isolation.attach_min_delta_r(enriched_bundle.copy())

    output_path = Path(output)
    BundleIO.save_bundle(enriched_bundle, output_path)
    return output_path


def main() -> None:
    """Parse the output filename and generate the enriched bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="hnl_selection_cutflow_enriched.pkl.gz",
        help="Destination trusted pickle bundle.",
    )
    args = parser.parse_args()
    print(f"Saved enriched bundle to {enrich_bundle(args.output).resolve()}")


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
