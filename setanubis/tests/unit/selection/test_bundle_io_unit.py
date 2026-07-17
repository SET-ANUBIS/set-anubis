"""Tests for trusted selection bundle persistence and legacy file names."""

from __future__ import annotations

import pickle

import pandas as pd
import pytest

from SetAnubis.core.Selection.adapters.output.WriteLoadSelectionDict import (
    load_bundle as legacy_load_bundle,
    save_bundle as legacy_save_bundle,
)
from SetAnubis.core.Selection.domain.DatasetSource import BundleIO


def _bundle() -> dict[str, pd.DataFrame]:
    return {"LLPs": pd.DataFrame({"eventNumber": [1, 2], "PID": [9900012, 9900012]})}


def test_gzip_bundle_is_detected_from_magic_bytes_even_with_pkl_suffix(tmp_path):
    path = tmp_path / "legacy_name.pkl"
    BundleIO.save_bundle(_bundle(), path)

    assert path.read_bytes().startswith(BundleIO.GZIP_MAGIC)
    pd.testing.assert_frame_equal(BundleIO.load_bundle(path)["LLPs"], _bundle()["LLPs"])


def test_plain_pickle_remains_readable_for_backward_compatibility(tmp_path):
    path = tmp_path / "plain.pkl"
    with path.open("wb") as stream:
        pickle.dump(_bundle(), stream)

    assert not path.read_bytes().startswith(BundleIO.GZIP_MAGIC)
    pd.testing.assert_frame_equal(BundleIO.load_bundle(path)["LLPs"], _bundle()["LLPs"])


def test_dataframe_round_trip_and_legacy_helpers(tmp_path):
    dataframe = pd.DataFrame({"value": [1.0, 2.0]})
    dataframe_path = tmp_path / "frame.pkl.gz"
    BundleIO.save_df(dataframe, dataframe_path)
    pd.testing.assert_frame_equal(BundleIO.load_df(dataframe_path), dataframe)

    bundle_path = tmp_path / "bundle.pkl"
    legacy_save_bundle(_bundle(), bundle_path)
    pd.testing.assert_frame_equal(legacy_load_bundle(bundle_path)["LLPs"], _bundle()["LLPs"])


def test_invalid_pickle_is_reported(tmp_path):
    path = tmp_path / "invalid.pkl"
    path.write_bytes(b"not a pickle")

    with pytest.raises((pickle.UnpicklingError, EOFError)):
        BundleIO.load_bundle(path)
