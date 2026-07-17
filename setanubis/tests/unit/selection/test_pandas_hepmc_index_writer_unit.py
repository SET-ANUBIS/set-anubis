"""Tests for deterministic HepMC CSV index creation."""

from __future__ import annotations

import pandas as pd

from SetAnubis.core.Selection.adapters.output.PandasHepMCIndexWriter import (
    PandasHepmcIndexWriterAdapter,
)
from SetAnubis.core.Selection.domain.Models import HepmcRef, IndexWriterConfig


def _item(event_id: str) -> HepmcRef:
    return HepmcRef(
        event_id=event_id,
        model="HNL",
        run_name=f"run-{event_id}",
        hepmc_path=f"/data/{event_id}.hepmc.gz",
        cross_section_pb=1.5,
        scan_params={"mN1": 1.0},
        scan_widths={"N1": 1e-12},
    )


def test_rewrite_mode_writes_extra_columns_and_deduplicates(tmp_path):
    path = tmp_path / "index.csv"
    writer = PandasHepmcIndexWriterAdapter()
    config = IndexWriterConfig(
        index_csv_path=str(path),
        extra_columns={"llp_id": 9900012},
    )

    first = writer.write_index([_item("a"), _item("b")], config)
    second = writer.write_index([_item("b"), _item("c")], config)

    assert (first.added_rows, first.total_rows_after, first.deduped_rows) == (2, 2, 0)
    assert (second.added_rows, second.total_rows_after, second.deduped_rows) == (1, 3, 1)
    assert set(second.selected_df["event_id"]) == {"b", "c"}
    stored = pd.read_csv(path, index_col=0)
    assert list(stored["event_id"]) == ["a", "b", "c"]
    assert set(stored["llp_id"]) == {9900012}


def test_batch_mode_appends_chunks_and_can_disable_deduplication(tmp_path):
    path = tmp_path / "batch" / "index.csv"
    writer = PandasHepmcIndexWriterAdapter()
    config = IndexWriterConfig(
        index_csv_path=str(path),
        rewrite_in_one_go=False,
        batch_size_rows=1,
        dedupe_on_event_id=False,
    )

    result = writer.write_index([_item("x"), _item("x")], config)

    assert result.added_rows == 2
    assert result.total_rows_after == 2
    assert result.deduped_rows == 0
    assert len(pd.read_csv(path, index_col=0)) == 2


def test_empty_and_corrupt_existing_index_are_handled(tmp_path):
    path = tmp_path / "index.csv"
    path.write_text('"unterminated', encoding="utf-8")
    writer = PandasHepmcIndexWriterAdapter()

    result = writer.write_index([], IndexWriterConfig(index_csv_path=str(path)))
    assert result.added_rows == 0
    assert result.total_rows_after == 0
    assert result.selected_df.empty

    new = writer._concat_and_reindex(pd.DataFrame(), pd.DataFrame({"event_id": ["z"]}))
    assert list(new.index) == [0]
    assert writer._concat_and_reindex(new, pd.DataFrame()).equals(new)
