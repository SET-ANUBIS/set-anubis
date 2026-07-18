"""Select HepMC artifacts from the event database and write a CSV index."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from SetAnubis.core.Selection.adapters.output.EventsDbHepMCSelector import (
    EventsDbHepmcSelectorAdapter,
)
from SetAnubis.core.Selection.adapters.output.PandasHepMCIndexWriter import (
    PandasHepmcIndexWriterAdapter,
)
from SetAnubis.core.Selection.domain.Models import HepmcSelectionQuery, IndexWriterConfig
from SetAnubis.examples._runtime import run_example_entrypoint


def main() -> int:
    """Select database-backed HepMC samples and materialize a processing index."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="db/EventsDatabase.db")
    parser.add_argument("--storage", default="db/EventsStorage")
    parser.add_argument("--model", default="SM_HeavyN_CKM_AllMasses_LO")
    parser.add_argument("--output", type=Path, default=Path("outputs/samples_to_process_SM.csv"))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    selector = EventsDbHepmcSelectorAdapter(db_path=args.db, storage_dir=args.storage)
    items = selector.select(HepmcSelectionQuery(model=args.model, limit=args.limit))

    extra_columns: dict[str, Any] = {"llp_id": 9900012, "geometry": "ceiling"}
    writer = PandasHepmcIndexWriterAdapter()
    result = writer.write_index(
        items,
        IndexWriterConfig(
            index_csv_path=str(args.output),
            rewrite_in_one_go=True,
            batch_size_rows=50_000,
            extra_columns=extra_columns,
            dedupe_on_event_id=True,
        ),
    )

    print(result.selected_df)
    print(f"Added rows: {result.added_rows}; total rows: {result.total_rows_after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
