"""Select one HNL subset from the event DB and persist only metadata plus cut flows."""

from __future__ import annotations

from pathlib import Path

from SetAnubis import (
    EventAccessor,
    EventDatabaseManager,
    EventsBundleSource,
    RunConfig,
    SelectionManager,
)
from SetAnubis.examples.Selection.compact_sample import (
    build_selection_config,
    build_selection_pipeline,
)
from SetAnubis.examples._runtime import run_example_entrypoint

ROOT = Path("outputs/selection_db_demo")
EVENT_DB = ROOT / "EventsDatabase.db"
EVENT_STORAGE = ROOT / "EventsStorage"
RESULTS_DB = ROOT / "SelectionResults.db"
MODEL = "SM_HeavyN_CKM_AllMasses_LO"


def main() -> None:
    """Filter electron-mixing samples, run selection, and store their cut flows."""
    events = EventAccessor(EventDatabaseManager(str(EVENT_DB), str(EVENT_STORAGE)))

    rows = events.query(
        model=MODEL,
        scan_params={"VeN1": 1.0e-6},
        has_bundle=True,
    )
    sources = [
        (row["run_name"], EventsBundleSource.from_event_database(events, row["id"]))
        for row in rows
    ]

    results = SelectionManager(build_selection_pipeline()).run_many(
        sources,
        build_selection_config(),
        RunConfig(),
        store=True,
        results_db=str(RESULTS_DB),
        analysis_name="baseline",
    )

    for sample in results.per_sample:
        print(sample.name, sample.cutFlow, sample.details.get("stored_result_id"))
    print(f"Stored selection results in {RESULTS_DB}")


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
