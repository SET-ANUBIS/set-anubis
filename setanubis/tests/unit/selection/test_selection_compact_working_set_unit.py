from __future__ import annotations

from pathlib import Path
import pandas as pd
from pandas.testing import assert_frame_equal

from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer


def test_selection_working_set_matches_full_bundle_for_selection_inputs():
    root = Path(__file__).resolve().parents[3]
    sample = root / "SetAnubis/examples/Selection/InputFiles/hnl_selection_cutflow_df.csv.gz"
    df = pd.read_csv(sample)

    analyzer = LLPAnalyzer(
        df,
        pt_min_cfg={"chargedTrack": 5.0, "neutralTrack": 5.0, "jet": 15.0},
    )
    full = analyzer.create_sample_dataframes(9900012)
    compact = analyzer.create_selection_working_set(9900012)

    assert_frame_equal(compact["LLPs"], full["LLPs"], check_exact=True, check_dtype=True)
    assert_frame_equal(
        compact["LLPchildren"], full["LLPchildren"], check_exact=True, check_dtype=True
    )

    for key in ("chargedFinalStates", "neutralFinalStates"):
        cols = list(compact[key].columns)
        assert_frame_equal(
            compact[key], full[key][cols], check_exact=True, check_dtype=True
        )

    assert set(compact) == {
        "LLPs", "LLPchildren", "chargedFinalStates", "neutralFinalStates"
    }
