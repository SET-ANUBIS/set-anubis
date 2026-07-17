"""Unit tests for selecting HepMC references from the event database."""

from SetAnubis.core.Selection.adapters.output.EventsDbHepMCSelector import (
    EventsDbHepmcSelectorAdapter,
)
from SetAnubis.core.Selection.domain.Models import HepmcSelectionQuery


class _Accessor:
    def __init__(self):
        self.query_args = None
        self.rows = [
            {
                "id": "event-a",
                "model": "HNL",
                "run_name": "run-a",
                "cross_section": 1.25,
                "scan_params_json": '{"mass": 5.0}',
                "scan_widths_json": "not-json",
            },
            {
                "id": "event-b",
                "model": "HNL",
                "run_name": "run-b",
                "cross_section": 2.5,
                "scan_params_json": None,
                "scan_widths_json": '{"9900012": 1e-12}',
            },
            {
                "id": "event-c",
                "model": "HNL",
                "run_name": "run-c",
                "cross_section": 3.5,
                "scan_params_json": "{}",
                "scan_widths_json": "{}",
            },
        ]

    def query(self, **kwargs):
        self.query_args = kwargs
        return self.rows

    def get_artifacts(self, event_id):
        if event_id == "event-b":
            return [{"kind": "banner", "sha256": "banner-sha"}]
        return [
            {"kind": "banner", "sha256": "banner-sha"},
            {"kind": "hepmc_gz", "sha256": f"{event_id}-sha"},
        ]

    def artifact_path(self, sha256):
        return f"/cas/{sha256}.gz"


def _adapter():
    adapter = EventsDbHepmcSelectorAdapter.__new__(EventsDbHepmcSelectorAdapter)
    adapter._acc = _Accessor()
    return adapter


def test_load_json_handles_empty_valid_and_invalid_values():
    assert EventsDbHepmcSelectorAdapter._load_json(None) is None
    assert EventsDbHepmcSelectorAdapter._load_json("") is None
    assert EventsDbHepmcSelectorAdapter._load_json("not-json") is None
    assert EventsDbHepmcSelectorAdapter._load_json('{"mass": 5}') == {"mass": 5}


def test_select_maps_artifacts_metadata_and_predicates():
    adapter = _adapter()
    query = HepmcSelectionQuery(
        model="HNL",
        sql_where="cross_section > ?",
        sql_params=(1.0,),
        predicate=lambda item: item.cross_section_pb < 3.0,
    )

    items = adapter.select(query)

    assert adapter._acc.query_args == {
        "model": "HNL",
        "where": "cross_section > ?",
        "params": (1.0,),
    }
    assert len(items) == 1
    assert items[0].event_id == "event-a"
    assert items[0].hepmc_path == "/cas/event-a-sha.gz"
    assert items[0].scan_params == {"mass": 5.0}
    assert items[0].scan_widths is None


def test_select_respects_zero_and_positive_limits():
    adapter = _adapter()
    assert adapter.select(HepmcSelectionQuery(limit=0)) == []

    items = adapter.select(HepmcSelectionQuery(limit=1))
    assert [item.event_id for item in items] == ["event-a"]
