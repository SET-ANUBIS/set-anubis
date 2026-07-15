from __future__ import annotations

import json
from typing import List

from SetAnubis.core.DataBase.domain.EventDatabaseManager import (
    EventAccessor,
    EventDatabaseManager,
)
from SetAnubis.core.Selection.domain.Models import HepmcRef, HepmcSelectionQuery
from SetAnubis.core.Selection.ports.output.IhepMCSelector import HepmcSelectorPort


class EventsDbHepmcSelectorAdapter(HepmcSelectorPort):
    def __init__(self, db_path: str, storage_dir: str, use_hardlinks: bool = False):
        self._db = EventDatabaseManager(
            db_path=db_path,
            storage_dir=storage_dir,
            use_hardlinks=use_hardlinks,
        )
        self._acc = EventAccessor(self._db)

    @staticmethod
    def _load_json(value: str | None):
        if not value:
            return None
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return None

    def select(self, query: HepmcSelectionQuery) -> List[HepmcRef]:
        rows = self._acc.query(
            model=query.model,
            where=query.sql_where,
            params=query.sql_params,
        )
        items: List[HepmcRef] = []

        for row in rows[: (query.limit or len(rows))]:
            artifacts = self._acc.get_artifacts(row["id"])

            hepmc_sha = next(
                (
                    artifact["sha256"]
                    for artifact in artifacts
                    if artifact["kind"] == "hepmc_gz"
                ),
                None,
            )
            if not hepmc_sha:
                continue

            item = HepmcRef(
                event_id=row["id"],
                model=row["model"],
                run_name=row["run_name"],
                hepmc_path=self._acc.artifact_path(hepmc_sha),
                cross_section_pb=row["cross_section"],
                scan_params=self._load_json(row["scan_params_json"]),
                scan_widths=self._load_json(row["scan_widths_json"]),
            )

            if query.predicate and not query.predicate(item):
                continue

            items.append(item)

        return items
