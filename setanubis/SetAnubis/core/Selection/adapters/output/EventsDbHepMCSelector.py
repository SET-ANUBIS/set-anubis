from __future__ import annotations
import json
from typing import List

from SetAnubis.core.Selection.domain.Models import HepmcSelectionQuery, HepmcRef
from SetAnubis.core.Selection.ports.output.IhepMCSelector import HepmcSelectorPort

# TODO : put an adapter.
from SetAnubis.core.DataBase.domain.EventDatabaseManagerv2 import EventDatabaseManager, EventAccessor  # type: ignore

class EventsDbHepmcSelectorAdapter(HepmcSelectorPort):

    def __init__(self, db_path: str, storage_dir: str, use_hardlinks: bool = False):
        self._db = EventDatabaseManager(db_path=db_path, storage_dir=storage_dir, use_hardlinks=use_hardlinks)
        self._acc = EventAccessor(self._db)

    def select(self, query: HepmcSelectionQuery) -> List[HepmcRef]:
        rows = self._acc.query(model=query.model, where=query.sql_where, params=query.sql_params)
        items: List[HepmcRef] = []

        for r in rows[: (query.limit or len(rows))]:
            ev_id = r["id"]
            arts = self._acc.get_artifacts(ev_id) 

            hepmc_sha = None
            for a in arts:
                if a["kind"] == "hepmc_gz":
                    hepmc_sha = a["sha256"]; break
            if not hepmc_sha:
                continue

            hepmc_path = self._acc.artifact_path(hepmc_sha)

            scan_params = None
            if r["scan_params_json"]:
                try: scan_params = json.loads(r["scan_params_json"])
                except Exception: pass
            scan_widths = None
            if r["scan_widths_json"]:
                try: scan_widths = json.loads(r["scan_widths_json"])
                except Exception: pass

            item = HepmcRef(
                event_id=r["id"],
                model=r["model"],
                run_name=r["run_name"],
                hepmc_path=hepmc_path,
                cross_section_pb=r["cross_section"],
                scan_params=scan_params,
                scan_widths=scan_widths,
            )

            if query.predicate and not query.predicate(item):
                continue

            items.append(item)

        return items
