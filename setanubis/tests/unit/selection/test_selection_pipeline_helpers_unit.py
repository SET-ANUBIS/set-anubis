"""Tests for selection-pipeline caches, builders, and preparation helpers."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

import SetAnubis.core.Selection.domain.SelectionPipeline as pipeline_mod
from SetAnubis.core.Selection.domain.ReweightTransformer import DataBundle
from SetAnubis.core.Selection.domain.SelectionEngine import RunConfig


def _complete_bundle() -> dict[str, pd.DataFrame]:
    return {
        "finalStates": pd.DataFrame({"value": [1]}),
        "LLPs": pd.DataFrame({"eventNumber": [1], "value": [2]}),
        "LLPchildren": pd.DataFrame({"value": [3]}),
        "finalStates_NoLLP": pd.DataFrame({"value": [4]}),
        "finalStates_Neutrinos": pd.DataFrame({"value": [5]}),
        "chargedFinalStates": pd.DataFrame({"eventNumber": [1], "value": [6]}),
        "neutralFinalStates": pd.DataFrame({"eventNumber": [1], "value": [7]}),
    }


def test_memory_and_file_caches_round_trip_values(tmp_path):
    memory = pipeline_mod.InMemoryCache()
    assert memory.get("missing") is None
    memory.set("answer", {"value": 42})
    assert memory.get("answer") == {"value": 42}

    disk = pipeline_mod.FileCache(str(tmp_path / "cache"))
    assert disk.get("missing") is None
    disk.set("answer", {"value": 42})
    assert disk.get("answer") == {"value": 42}
    assert not list((tmp_path / "cache").glob("*.tmp"))


def test_pipeline_builder_copies_configuration_and_transforms():
    before = lambda frame: frame
    after = lambda bundle: bundle
    builder = (
        pipeline_mod.SelectionPipelineBuilder()
        .set_options(add_jets=False, compute_isolation=False, selection_mode="2dv")
        .add_pre_df_transform(before)
        .add_post_bundle_transform(after)
        .set_reweighter(1e-9, 9900012, seed=7)
    )
    pipeline = builder.build()

    assert not pipeline.options.add_jets
    assert pipeline.options.selection_mode == "2dv"
    assert pipeline.pre_df_transforms == [before]
    assert pipeline.post_bundle_transforms == [after]
    assert pipeline.reweighter is not None

    # Built pipelines own list copies rather than sharing mutable builder state.
    builder.add_pre_df_transform(lambda frame: frame.copy())
    assert pipeline.pre_df_transforms == [before]
    assert (
        pipeline_mod.SelectionPipelineBuilder()
        .set_reweighter(None, None)
        .build()
        .reweighter
        is None
    )


def test_reweight_gate_and_extra_bundle_entries_are_preserved():
    class FakeReweighter:
        def __init__(self):
            self.calls = 0

        def apply(self, bundle: DataBundle) -> DataBundle:
            self.calls += 1
            return replace(bundle, LLPs=bundle.LLPs.assign(reweighted=True))

    fake = FakeReweighter()
    pipeline = pipeline_mod.SelectionPipeline(
        engine=object(),
        options=pipeline_mod.PipelineOptions(enable_reweight_gate=True),
        pre_df_transforms=[],
        post_bundle_transforms=[],
        reweighter=fake,
    )
    bundle = _complete_bundle()
    bundle["metadata"] = pd.DataFrame({"tag": ["kept"]})

    assert pipeline._maybe_reweight(bundle, RunConfig(reweightLifetime=False)) is bundle
    assert fake.calls == 0

    result = pipeline._maybe_reweight(bundle, RunConfig(reweightLifetime=True))
    assert fake.calls == 1
    assert result["LLPs"]["reweighted"].tolist() == [True]
    assert result["metadata"].equals(bundle["metadata"])


def test_jet_and_isolation_preparation_calls_only_missing_steps(monkeypatch):
    calls: list[str] = []

    def fake_create_jet_df(events, charged, neutral):
        calls.append(f"jets:{events.tolist()}")
        return pd.DataFrame({"eventNumber": events, "pt": 20.0, "p": 20.0})

    class FakeIsolationComputer:
        def __init__(self, selection):
            calls.append(f"isolation:{selection}")

        def attach_min_delta_r(self, bundle):
            return bundle["LLPs"].assign(minDeltaR_Jets=0.8, minDeltaR_Tracks=0.9)

    monkeypatch.setattr(pipeline_mod, "createJetDF", fake_create_jet_df)
    monkeypatch.setattr(pipeline_mod, "IsolationComputer", FakeIsolationComputer)

    pipeline = pipeline_mod.SelectionPipelineBuilder().build()
    bundle = {
        "LLPs": pd.DataFrame({"eventNumber": [1], "eta": [0.0], "phi": [0.0]}),
        "chargedFinalStates": pd.DataFrame(
            {"eventNumber": [1], "pt": [10.0], "p": [10.0]}
        ),
        "neutralFinalStates": pd.DataFrame(
            {"eventNumber": [1], "pt": [10.0], "p": [10.0]}
        ),
    }
    result = pipeline._ensure_jets_and_isolation(bundle, sel_cfg="selection")
    assert calls == ["jets:[1]", "isolation:selection"]
    assert "finalStatePromptJets" in result
    assert result["LLPs"]["minDeltaR_Jets"].tolist() == [0.8]

    calls.clear()
    prepared = dict(result)
    assert pipeline._ensure_jets_and_isolation(prepared, "selection")[
        "finalStatePromptJets"
    ].equals(prepared["finalStatePromptJets"])
    assert calls == []
