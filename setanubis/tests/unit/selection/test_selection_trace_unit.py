"""Tests for intermediate selection snapshots and report exports."""

from __future__ import annotations

import json

from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource
from SetAnubis.core.Selection.domain.SelectionEngine import (
    MinDR,
    RunConfig,
    SelectionConfig,
)
from SetAnubis.core.Selection.domain.SelectionPipeline import SelectionPipelineBuilder
from SetAnubis.examples.Selection.example_selection_trace_report import (
    DemonstrationGeometry,
    build_demo_bundle,
    run_example,
)


def _run_traced_selection():
    pipeline = (
        SelectionPipelineBuilder()
        .set_options(add_jets=False, compute_isolation=False)
        .build()
    )
    return pipeline.run(
        EventsBundleSource.from_bundle_dict(build_demo_bundle()),
        SelectionConfig(
            geometry=DemonstrationGeometry(),
            minMET=30.0,
            minDR=MinDR(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
            nStations=2,
            nIntersections=2,
            nTracks=1,
        ),
        RunConfig(capture_intermediate=True),
    )


def test_selection_trace_records_each_stage_and_failure_reason():
    result = _run_traced_selection()
    trace = result["trace"]

    assert list(trace.stage_dataframes) == [
        "Original",
        "LLPDecay",
        "InCavern",
        "NotInATLAS",
        "Geometry",
        "Tracker",
        "MET",
        "IsoJets",
        "IsoCharged",
        "IsoAll",
        "Final",
    ]
    assert [len(frame) for frame in trace.stage_dataframes.values()] == [
        8,
        7,
        6,
        5,
        4,
        3,
        2,
        1,
        2,
        1,
        1,
    ]

    candidates = trace.candidate_summary.set_index("eventNumber")
    assert candidates.loc[100, "first_failed_stage"] == "LLPDecay"
    assert candidates.loc[101, "first_failed_stage"] == "InCavern"
    assert candidates.loc[102, "first_failed_stage"] == "NotInATLAS"
    assert candidates.loc[103, "first_failed_stage"] == "Geometry"
    assert candidates.loc[104, "first_failed_stage"] == "Tracker"
    assert candidates.loc[105, "first_failed_stage"] == "MET"
    assert candidates.loc[106, "first_failed_stage"] == "IsoJets"
    assert candidates.loc[107, "first_failed_stage"] is None
    assert candidates["first_failed_stage"].dtype == object
    assert candidates["last_passed_stage"].dtype == object
    assert candidates.loc[107, "last_passed_stage"] == "Final"

    events = trace.event_summary.set_index("eventNumber")
    assert events.loc[107, "passed_Final"]
    assert not events.loc[106, "passed_Final"]
    assert events.loc[106, "last_passed_stage"] == "IsoCharged"


def test_selection_trace_exports_json_html_and_optional_records(tmp_path):
    trace = _run_traced_selection()["trace"]
    json_path = trace.write_json(
        tmp_path / "trace-with-records.json", include_stage_records=True
    )
    html_path = trace.write_html(tmp_path / "trace.html", title="Trace test")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["stages"][0]["name"] == "Original"
    assert len(payload["stages"][0]["records"]) == 8
    assert payload["events"][-1]["last_passed_stage"] == "Final"

    document = html_path.read_text(encoding="utf-8")
    assert "Trace test" in document
    assert 'id="selection-trace-data"' in document
    embedded = document.split('type="application/json">', 1)[1].split("</script>", 1)[0]
    assert json.loads(embedded)["stages"][-1]["name"] == "Final"


def test_selection_trace_example_writes_matching_report_files(tmp_path):
    json_path, html_path = run_example(tmp_path)
    assert json_path.name == "selection_trace_demo.json"
    assert html_path.name == "selection_trace_demo.html"
    assert json_path.is_file() and html_path.is_file()


def test_selection_trace_is_opt_in():
    pipeline = (
        SelectionPipelineBuilder()
        .set_options(add_jets=False, compute_isolation=False)
        .build()
    )
    result = pipeline.run(
        EventsBundleSource.from_bundle_dict(build_demo_bundle()),
        SelectionConfig(geometry=DemonstrationGeometry()),
        RunConfig(),
    )
    assert "trace" not in result
