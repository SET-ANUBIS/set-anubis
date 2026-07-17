"""Unit tests for deterministic selection data sources and cache identities."""

from __future__ import annotations

import pandas as pd
import pytest

import SetAnubis.core.Selection.domain.DatasetSource as dataset_source


class _FakeAnalyzer:
    def __init__(self, dataframe, pt_min_cfg):
        self.dataframe = dataframe
        self.pt_min_cfg = pt_min_cfg

    def create_sample_dataframes(self, llpid):
        return {"LLPs": self.dataframe.assign(llp_pid=llpid)}


def test_ready_bundle_is_returned_without_reprocessing():
    bundle = {"LLPs": pd.DataFrame({"eventNumber": [1]})}
    source = dataset_source.EventsBundleSource.from_bundle_dict(bundle)
    assert source.materialize() is bundle


def test_dataframe_source_accepts_no_pre_transforms(monkeypatch):
    monkeypatch.setattr(dataset_source, "LLPAnalyzer", _FakeAnalyzer)
    dataframe = pd.DataFrame({"eventNumber": [1, 2], "value": [3.0, 4.0]})
    source = dataset_source.EventsBundleSource.from_events_dataframe(dataframe)

    bundle = source.materialize()

    assert bundle["LLPs"]["llp_pid"].tolist() == [9900012, 9900012]


def test_dataframe_transform_and_cache_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(dataset_source, "LLPAnalyzer", _FakeAnalyzer)
    dataframe = pd.DataFrame({"eventNumber": [1], "value": [2.0]})
    source = dataset_source.EventsBundleSource.from_events_dataframe(
        dataframe,
        cache_dir=str(tmp_path),
    )

    first = source.materialize([lambda frame: frame.assign(value=frame["value"] * 2)])
    assert first["LLPs"]["value"].tolist() == [4.0]

    second = dataset_source.EventsBundleSource.from_events_dataframe(
        dataframe,
        cache_dir=str(tmp_path),
    ).materialize()
    assert second["LLPs"]["value"].tolist() == [4.0]


def test_cache_fingerprints_are_compact_sha256(tmp_path):
    path = tmp_path / "sample.dat"
    path.write_text("one", encoding="utf-8")
    path_hash = dataset_source._fingerprint_paths([str(path)])
    df_hash = dataset_source._fingerprint_df(pd.DataFrame({"x": [1, 2]}))

    assert len(path_hash) == len(df_hash) == 16
    assert all(char in "0123456789abcdef" for char in path_hash + df_hash)


def test_missing_source_is_rejected():
    with pytest.raises(ValueError, match="Provide either"):
        dataset_source.EventsBundleSource().materialize()
