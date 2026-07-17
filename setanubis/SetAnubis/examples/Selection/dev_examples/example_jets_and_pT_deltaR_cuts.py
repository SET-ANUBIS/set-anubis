"""Add prompt jets and isolation distances to the packaged HNL sample."""

from pathlib import Path

import numpy as np
import pandas as pd

from SetAnubis.core.Geometry.adapters.ATLASCavernGeometry import ATLASCavernGeometry
from SetAnubis.core.Geometry.adapters.ATLASCavernGeometryConfig import (
    ATLASCavernGeometryConfig,
)
from SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter import (
    SelectionGeometryAdapter,
)
from SetAnubis.core.Selection.domain.DatasetSource import BundleIO
from SetAnubis.core.Selection.domain.JetBuilder import createJetDF
from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer
from SetAnubis.core.Selection.domain.SelectionEngine import (
    MinDR,
    MinThresholds,
    SelectionConfig,
)
from SetAnubis.core.Selection.domain.isolation import IsolationComputer

INPUT_DIR = Path(__file__).resolve().parent.parent / "InputFiles"
CSV_FILE = INPUT_DIR / "hnl_df.csv"
BUNDLE_CANDIDATES = (
    INPUT_DIR / "samples_dfs_hnl.pkl.gz",
    INPUT_DIR / "samples_dfs_hnl.pkl",  # Legacy name; gzip is detected by header.
)
OUTPUT_FILE = Path("samples_dfs_hnl_with_jet_deltaR.pkl.gz")


def load_or_build_bundle():
    """Load a prepared bundle, or build it from the packaged CSV when absent."""
    for candidate in BUNDLE_CANDIDATES:
        if candidate.is_file():
            print(f"Loading trusted selection bundle: {candidate}")
            return BundleIO.load_bundle(candidate)

    # The repository ships the CSV, so this example remains runnable without a
    # generated pickle from a previous example.
    print(f"No bundle found; building one from {CSV_FILE}")
    dataframe = pd.read_csv(CSV_FILE)
    analyzer = LLPAnalyzer(dataframe.copy(), pt_min_cfg={"chargedTrack": 0.5})
    return analyzer.create_sample_dataframes(llpid=9900012)


if __name__ == "__main__":
    sample_dfs = load_or_build_bundle()
    charged = sample_dfs["chargedFinalStates"].copy()
    neutral = sample_dfs["neutralFinalStates"].copy()

    # Build the canonical geometry backend used by the current selection engine.
    geometry = ATLASCavernGeometry.create(
        ATLASCavernGeometryConfig(
            mode="ceiling",
            origin="IP",
            rpc_eff=1.0,
            n_rpcs_per_layer=1,
            use_cache=False,
        )
    )
    selection_geometry = SelectionGeometryAdapter(geometry)

    selection_config = SelectionConfig(
        geometry=selection_geometry,
        minMET=30.0,
        minP=MinThresholds(LLP=0.1, chargedTrack=0.1, neutralTrack=0.1, jet=0.1),
        minPt=MinThresholds(LLP=0.0, chargedTrack=5.0, neutralTrack=5.0, jet=15.0),
        minDR=MinDR(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
        nStations=2,
        nIntersections=2,
        nTracks=1,
    )

    # Cluster prompt final states event by event before computing LLP isolation.
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
        event_numbers, charged, neutral
    )

    isolation = IsolationComputer(selection=selection_config)
    enriched_bundle["LLPs"] = isolation.attach_min_delta_r(enriched_bundle.copy())

    print(enriched_bundle["LLPs"].head())
    BundleIO.save_bundle(enriched_bundle, OUTPUT_FILE)
    print(f"Saved enriched selection bundle to {OUTPUT_FILE.resolve()}")
