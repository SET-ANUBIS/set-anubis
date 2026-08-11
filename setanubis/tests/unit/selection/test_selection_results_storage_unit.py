"""Unit tests for optional cut-flow persistence from SelectionPipeline."""

from __future__ import annotations

import importlib.util
import sys
import types

import pandas as pd
import pytest

# SelectionPipeline imports the optional FastJet stack at module import time.
# These tiny stubs keep this storage-only unit test independent of native wheels.
if importlib.util.find_spec("awkward") is None:
    awkward = types.ModuleType("awkward")
    awkward.from_numpy = lambda value: value
    sys.modules["awkward"] = awkward
if importlib.util.find_spec("fastjet") is None:
    fastjet = types.ModuleType("fastjet")
    fastjet.antikt_algorithm = 1
    fastjet.JetDefinition = lambda *args, **kwargs: object()
    fastjet._pyjet = types.SimpleNamespace(AwkwardClusterSequence=object)
    fastjet.ClusterSequence = types.SimpleNamespace()
    sys.modules["fastjet"] = fastjet

from SetAnubis.core.DataBase.domain.SelectionResultsDatabaseManager import (
    SelectionResultsAccessor,
)
from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource
from SetAnubis.core.Selection.domain.SelectionEngine import RunConfig, SelectionConfig
from SetAnubis.core.Selection.domain.SelectionPipeline import (
    PipelineOptions,
    SelectionPipeline,
)


class _Geometry:
    default_decay_region = "demo"
    default_fiducial_radius = 1.0


class _Engine:
    def apply_selection(self, bundle, run_cfg, sel_cfg):
        return {
            "cutFlow": {"nLLP_original": 4, "nLLP_Final": 2},
            "cutIndices": {},
            "finalDF": pd.DataFrame(),
        }

    def apply_2dv_selection(self, bundle, run_cfg, sel_cfg):
        return self.apply_selection(bundle, run_cfg, sel_cfg)


def test_pipeline_can_store_cutflow_from_database_provenance(tmp_path):
    source = EventsBundleSource.from_bundle_dict(
        {"LLPs": pd.DataFrame(), "LLPchildren": pd.DataFrame()},
        dataset_id="event-1",
        metadata={
            "event_id": "event-1",
            "event_hash": "run-hash",
            "bundle_sha256": "bundle-sha",
            "model": "HNL",
            "campaign": "campaign-a",
            "scan_params": {"VeN1": 1.0e-6},
            "masses": {"9900012": 1.0},
        },
    )
    pipeline = SelectionPipeline(
        engine=_Engine(),
        options=PipelineOptions(add_jets=False, compute_isolation=False),
        pre_df_transforms=[],
        post_bundle_transforms=[],
    )
    results_db = tmp_path / "SelectionResults.db"

    result = pipeline.run(
        source,
        SelectionConfig(geometry=_Geometry()),
        RunConfig(),
        store=True,
        results_db=results_db,
        analysis_name="baseline",
    )

    assert "stored_result_id" in result
    stored = SelectionResultsAccessor(str(results_db)).get_result(result["stored_result_id"])
    assert stored is not None
    assert stored["event_id"] == "event-1"
    assert stored["cutFlow"]["nLLP_Final"] == 2


def test_pipeline_requires_event_provenance_when_storage_is_requested(tmp_path):
    source = EventsBundleSource.from_bundle_dict(
        {"LLPs": pd.DataFrame(), "LLPchildren": pd.DataFrame()}
    )
    pipeline = SelectionPipeline(
        engine=_Engine(),
        options=PipelineOptions(add_jets=False, compute_isolation=False),
        pre_df_transforms=[],
        post_bundle_transforms=[],
    )
    with pytest.raises(ValueError, match="event_id"):
        pipeline.run(
            source,
            SelectionConfig(geometry=_Geometry()),
            RunConfig(),
            store=True,
            results_db=tmp_path / "SelectionResults.db",
        )
