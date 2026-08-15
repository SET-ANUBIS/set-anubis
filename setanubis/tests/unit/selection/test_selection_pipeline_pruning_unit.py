from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
import types

import numpy as np
import pandas as pd

# SelectionPipeline imports JetBuilder, which has optional native dependencies.
if importlib.util.find_spec("awkward") is None:
    awkward = types.ModuleType("awkward")
    awkward.__spec__ = importlib.machinery.ModuleSpec("awkward", loader=None)
    awkward.from_numpy = lambda value: value
    awkward.to_numpy = np.asarray
    sys.modules["awkward"] = awkward
if importlib.util.find_spec("fastjet") is None:
    fastjet = types.ModuleType("fastjet")
    fastjet.__spec__ = importlib.machinery.ModuleSpec("fastjet", loader=None)
    fastjet.antikt_algorithm = 1
    fastjet.JetDefinition = lambda *args, **kwargs: object()
    fastjet._pyjet = types.SimpleNamespace(AwkwardClusterSequence=object)
    fastjet.ClusterSequence = types.SimpleNamespace()
    sys.modules["fastjet"] = fastjet

from SetAnubis.core.Selection.domain.SelectionPipeline import SelectionPipelineBuilder


def test_selection_ready_pruning_keeps_only_engine_frames_after_isolation():
    pipeline = SelectionPipelineBuilder().build()
    llps = pd.DataFrame(
        {
            "eventNumber": [0, 1],
            "minDeltaR_Jets": [0.7, -1.0],
            "minDeltaR_Tracks": [0.8, -1.0],
        },
        index=[5, 10],
    )
    children = pd.DataFrame({"eventNumber": [0], "LLPindex": [5]}, index=[6])
    bundle = {
        "LLPs": llps,
        "LLPchildren": children,
        "finalStates": pd.DataFrame({"x": [1]}),
        "chargedFinalStates": pd.DataFrame({"x": [2]}),
        "neutralFinalStates": pd.DataFrame({"x": [3]}),
        "finalStatePromptJets": pd.DataFrame({"x": [4]}),
    }

    out = pipeline._prune_selection_ready_bundle(bundle)
    assert list(out) == ["LLPs", "LLPchildren"]
    assert out["LLPs"] is llps
    assert out["LLPchildren"] is children


def test_pruning_is_not_done_before_isolation_exists():
    pipeline = SelectionPipelineBuilder().build()
    bundle = {
        "LLPs": pd.DataFrame({"eventNumber": [0]}),
        "LLPchildren": pd.DataFrame(),
        "chargedFinalStates": pd.DataFrame({"eventNumber": [0]}),
    }
    assert pipeline._prune_selection_ready_bundle(bundle) is bundle
