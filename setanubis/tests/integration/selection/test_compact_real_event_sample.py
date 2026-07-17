"""Integration tests for the compact real-event selection example dataset."""

from __future__ import annotations

from importlib.resources import as_file

import pandas as pd

from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource
from SetAnubis.core.Selection.domain.SelectionEngine import RunConfig
from SetAnubis.examples.Selection.compact_sample import (
    build_selection_config,
    build_selection_pipeline,
    compact_hepmc_resource,
    input_resource,
    load_compact_bundle,
    load_compact_dataframe,
    load_compact_manifest,
)

_EXPECTED_FAILURES = [
    "InCavern",
    "NotInATLAS",
    "Geometry",
    "Tracker",
    "MET",
    "IsoJets",
    None,
]


def test_compact_sample_is_small_and_has_consistent_provenance():
    """Keep all three representations compact and aligned by event number."""
    resources = [
        input_resource("hnl_selection_cutflow.hepmc.gz"),
        input_resource("hnl_selection_cutflow_df.csv.gz"),
        input_resource("hnl_selection_cutflow_bundle.pkl.gz"),
        input_resource("hnl_selection_cutflow_manifest.json"),
    ]
    total_size = 0
    for resource in resources:
        with as_file(resource) as path:
            total_size += path.stat().st_size
    assert total_size < 1_000_000

    dataframe = load_compact_dataframe()
    bundle = load_compact_bundle()
    manifest = load_compact_manifest()

    assert dataframe["eventNumber"].drop_duplicates().tolist() == list(range(7))
    assert bundle["LLPs"]["eventNumber"].tolist() == list(range(7))
    assert [event["event_number"] for event in manifest["events"]] == list(range(7))
    assert [event["expected_first_failed_stage"] for event in manifest["events"]] == _EXPECTED_FAILURES

    with as_file(compact_hepmc_resource()) as path:
        assert path.read_bytes().startswith(b"\x1f\x8b")


def test_compact_sample_reproduces_each_observed_selection_outcome():
    """Run the public pipeline and verify one real event per observed outcome."""
    result = build_selection_pipeline().run(
        EventsBundleSource.from_bundle_dict(load_compact_bundle()),
        build_selection_config(),
        RunConfig(capture_intermediate=True),
    )
    summary = result["trace"].candidate_summary.sort_values("eventNumber")
    actual = [None if pd.isna(value) else value for value in summary["first_failed_stage"]]

    assert summary["eventNumber"].tolist() == list(range(7))
    assert actual == _EXPECTED_FAILURES
    assert result["finalDF"]["eventNumber"].tolist() == [6]
