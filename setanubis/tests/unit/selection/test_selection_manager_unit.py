"""Unit tests for aggregating results from multiple selection sources."""

from __future__ import annotations

import pandas as pd

from SetAnubis.core.Selection.domain.SelectionManager import SelectionManager


class FakePipeline:
    def run(self, source, sel_cfg, run_cfg):
        return {
            "cutFlow": source["cutflow"],
            "finalDF": pd.DataFrame({"event": source["events"]}),
            "metadata": source["name"],
        }


def test_run_many_preserves_details_and_sums_numeric_cutflow_values():
    manager = SelectionManager(FakePipeline())
    result = manager.run_many(
        named_sources=[
            ("first", {"name": "A", "events": [1], "cutflow": {"all": 3, "label": "x"}}),
            ("second", {"name": "B", "events": [2, 3], "cutflow": {"all": 4, "pass": 2.5}}),
        ],
        sel_cfg=object(),
        run_cfg=object(),
    )

    assert [sample.name for sample in result.per_sample] == ["first", "second"]
    assert result.per_sample[0].details == {"metadata": "A"}
    assert list(result.per_sample[1].finalDF["event"]) == [2, 3]
    assert result.cutflow_sum == {"all": 7, "pass": 2.5}


def test_run_many_accepts_an_empty_source_list():
    result = SelectionManager(FakePipeline()).run_many([], object(), object())
    assert result.per_sample == []
    assert result.cutflow_sum == {}
