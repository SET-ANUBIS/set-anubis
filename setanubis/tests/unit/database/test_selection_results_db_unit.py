"""Unit tests for the lightweight selection-results database."""

from __future__ import annotations

from collections import OrderedDict

import pytest

from SetAnubis.core.DataBase.domain.SelectionResultsDatabaseManager import (
    SelectionResultsAccessor,
    SelectionResultsDatabaseManager,
)


def _metadata() -> dict:
    return {
        "event_id": "event-123",
        "event_hash": "run-hash-abc",
        "bundle_sha256": "bundle-sha-def",
        "model": "SM_HeavyN_CKM_AllMasses_LO",
        "campaign": "hnl_demo",
        "run_name": "run_00_decayed_1",
        "llp_pid": 9900012,
        "cross_section": 1.0e-3,
        "seed": 42,
        "masses": {"9900012": 1.0},
        "scan_params": {"VeN1": 1.0e-6},
        "scan_widths": {"width#9900012": 1.0e-15},
    }


def test_store_query_and_export_cutflow(tmp_path):
    manager = SelectionResultsDatabaseManager(tmp_path / "SelectionResults.db")
    accessor = SelectionResultsAccessor(manager)
    cut_flow = OrderedDict(
        [
            ("nLLP_original", 7),
            ("nLLP_InCavern", 6),
            ("nLLP_Final", 1),
            ("nLLP_Final_weighted", 0.5),
        ]
    )

    result_id = manager.store_result(
        event_metadata=_metadata(),
        cut_flow=cut_flow,
        selection_config={"minMET": 30.0},
        run_config={"reweightLifetime": False},
        pipeline_options={"selection_mode": "standard"},
        analysis_name="baseline",
    )

    result = accessor.get_result(result_id)
    assert result is not None
    assert result["event_id"] == "event-123"
    assert result["event_hash"] == "run-hash-abc"
    assert result["bundle_sha256"] == "bundle-sha-def"
    assert result["cutFlow"] == cut_flow

    rows = accessor.query(
        model="SM_HeavyN_CKM_AllMasses_LO",
        campaign="hnl_demo",
        scan_params={"VeN1": 1.0e-6},
        masses={9900012: 1.0},
        cut_name="nLLP_Final",
        cut_min=1,
    )
    assert len(rows) == 1 and rows[0]["result_id"] == result_id

    frame = accessor.to_dataframe(analysis_name="baseline")
    assert frame.loc[0, "param:VeN1"] == pytest.approx(1.0e-6)
    assert frame.loc[0, "mass:9900012"] == pytest.approx(1.0)
    assert frame.loc[0, "nLLP_Final"] == 1

    csv_path = tmp_path / "cuts.csv"
    assert accessor.export_csv(csv_path, analysis_name="baseline") == str(csv_path)
    assert csv_path.is_file()


def test_conflict_policies_keep_one_result_per_event_configuration_label(tmp_path):
    manager = SelectionResultsDatabaseManager(tmp_path / "SelectionResults.db")
    accessor = SelectionResultsAccessor(manager)
    kwargs = dict(
        event_metadata=_metadata(),
        selection_config={"minMET": 30.0},
        run_config={"reweightLifetime": False},
        pipeline_options={"selection_mode": "standard"},
        analysis_name="baseline",
    )

    first = manager.store_result(cut_flow={"nLLP_Final": 1}, **kwargs)
    skipped = manager.store_result(cut_flow={"nLLP_Final": 9}, on_conflict="skip", **kwargs)
    assert skipped == first
    assert accessor.get_cutflow(first)["nLLP_Final"] == 1

    replaced = manager.store_result(cut_flow={"nLLP_Final": 2}, on_conflict="replace", **kwargs)
    assert replaced == first
    assert accessor.get_cutflow(first)["nLLP_Final"] == 2

    with pytest.raises(ValueError, match="already exists"):
        manager.store_result(cut_flow={"nLLP_Final": 3}, on_conflict="error", **kwargs)
