"""Lightweight persistence for selection cut-flow results.

The event database remains the source of heavy dataframe bundles.  This module
stores only provenance/physics metadata, the selection configuration, and the
small numerical cut flow produced for each source event.  Results are kept in a
single SQLite file so they stay queryable without creating one CSV per sample.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sqlite3
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    import pandas as pd
except Exception:  # pragma: no cover - pandas is an optional dependency here
    pd = None


class _ClosingConnection(sqlite3.Connection):
    """SQLite connection that closes after a transaction context exits."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _json_safe(value: Any) -> Any:
    """Convert common Python/scientific objects into deterministic JSON data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            pass
    if hasattr(value, "tolist"):
        try:
            return _json_safe(value.tolist())
        except Exception:
            pass
    return repr(value)


def _json_dumps(value: Any) -> str:
    """Serialize JSON in a stable form suitable for hashes and storage."""
    return json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _loads(value: Optional[str], default: Any) -> Any:
    """Decode a JSON column and return *default* for missing/invalid values."""
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _json_path(key: Any) -> str:
    """Return a SQLite JSON path for arbitrary dictionary keys."""
    escaped = str(key).replace("\\", "\\\\").replace('"', '\\"')
    return f'$."{escaped}"'


@dataclass(frozen=True)
class SelectionResultRecord:
    """Metadata for one persisted cut-flow result."""

    result_id: str
    event_id: str
    event_hash: Optional[str]
    bundle_sha256: Optional[str]
    selection_hash: str
    analysis_name: str
    created_at: str
    model: Optional[str]
    campaign: Optional[str]
    run_name: Optional[str]
    llp_pid: Optional[int]
    cross_section: Optional[float]
    seed: Optional[int]


class SelectionResultsDatabaseManager:
    """Create and write a lightweight SQLite selection-results database.

    The original event ``event_id``, content ``event_hash`` (the event DB
    ``run_hash``), and ``bundle_sha256`` are copied verbatim so a result can
    always be traced back to the heavy event database.  ``result_id`` is a
    separate deterministic identifier because the same event may be selected
    with multiple configurations or analysis labels.
    """

    VALID_CONFLICT_POLICIES = {"replace", "skip", "error"}

    def __init__(self, db_path: str = "db/SelectionResults.db") -> None:
        self.db_path = str(db_path)
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)) or ".", exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, factory=_ClosingConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS selection_results (
                    result_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    event_hash TEXT,
                    bundle_sha256 TEXT,
                    selection_hash TEXT NOT NULL,
                    analysis_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    model TEXT,
                    campaign TEXT,
                    run_name TEXT,
                    llp_pid INTEGER,
                    cross_section REAL,
                    seed INTEGER,
                    masses_json TEXT,
                    scan_params_json TEXT,
                    scan_widths_json TEXT,
                    source_metadata_json TEXT,
                    selection_config_json TEXT NOT NULL,
                    run_config_json TEXT NOT NULL,
                    pipeline_options_json TEXT NOT NULL,
                    extra_metadata_json TEXT,
                    n_cuts INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(event_id, selection_hash, analysis_name)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS selection_cuts (
                    result_id TEXT NOT NULL REFERENCES selection_results(result_id) ON DELETE CASCADE,
                    cut_order INTEGER NOT NULL,
                    cut_name TEXT NOT NULL,
                    cut_value REAL NOT NULL,
                    value_type TEXT NOT NULL,
                    weighted INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(result_id, cut_name)
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sel_event ON selection_results(event_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sel_event_hash ON selection_results(event_hash);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sel_bundle ON selection_results(bundle_sha256);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sel_model ON selection_results(model);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sel_campaign ON selection_results(campaign);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sel_analysis ON selection_results(analysis_name);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sel_signature ON selection_results(selection_hash);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sel_cut_name ON selection_cuts(cut_name);")

    @staticmethod
    def selection_hash(
        selection_config: Mapping[str, Any],
        run_config: Mapping[str, Any],
        pipeline_options: Mapping[str, Any],
    ) -> str:
        """Return a deterministic SHA-256 signature for a selection setup."""
        payload = {
            "selection_config": selection_config,
            "run_config": run_config,
            "pipeline_options": pipeline_options,
        }
        return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()

    @staticmethod
    def result_id(event_id: str, selection_hash: str, analysis_name: str) -> str:
        """Return a deterministic result identifier for event/config/analysis."""
        payload = f"{event_id}\0{selection_hash}\0{analysis_name}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def store_result(
        self,
        *,
        event_metadata: Mapping[str, Any],
        cut_flow: Mapping[str, Any],
        selection_config: Mapping[str, Any],
        run_config: Mapping[str, Any],
        pipeline_options: Mapping[str, Any],
        analysis_name: str = "default",
        on_conflict: str = "replace",
        extra_metadata: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """Persist one selection cut flow and return its ``result_id``.

        ``on_conflict`` controls a repeated event/config/analysis combination:
        ``replace`` refreshes the row and cuts, ``skip`` keeps the existing
        result, and ``error`` raises ``ValueError``.
        """
        policy = str(on_conflict).lower().strip()
        if policy not in self.VALID_CONFLICT_POLICIES:
            raise ValueError(
                f"on_conflict must be one of {sorted(self.VALID_CONFLICT_POLICIES)}, got {on_conflict!r}"
            )
        event_id = str(event_metadata.get("event_id") or "").strip()
        if not event_id:
            raise ValueError("event_metadata must contain the source event_id")
        analysis_name = str(analysis_name or "default").strip() or "default"

        signature = self.selection_hash(selection_config, run_config, pipeline_options)
        result_id = self.result_id(event_id, signature, analysis_name)

        numeric_cuts: List[Tuple[int, str, float, str, int]] = []
        for order, (name, raw_value) in enumerate(cut_flow.items()):
            if isinstance(raw_value, bool):
                value = float(int(raw_value))
                value_type = "bool"
            else:
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    continue
                value_type = "int" if isinstance(raw_value, int) else "float"
            numeric_cuts.append(
                (order, str(name), value, value_type, int(str(name).endswith("_weighted")))
            )

        masses = event_metadata.get("masses") or {}
        scan_params = event_metadata.get("scan_params") or {}
        scan_widths = event_metadata.get("scan_widths") or {}

        with self._conn() as conn:
            existing = conn.execute(
                """
                SELECT result_id FROM selection_results
                WHERE event_id=? AND selection_hash=? AND analysis_name=?
                """,
                (event_id, signature, analysis_name),
            ).fetchone()
            if existing:
                if policy == "skip":
                    return str(existing["result_id"])
                if policy == "error":
                    raise ValueError(
                        "Selection result already exists for "
                        f"event_id={event_id}, analysis_name={analysis_name}, selection_hash={signature}"
                    )
                conn.execute("DELETE FROM selection_results WHERE result_id=?", (existing["result_id"],))

            conn.execute(
                """
                INSERT INTO selection_results (
                    result_id, event_id, event_hash, bundle_sha256, selection_hash,
                    analysis_name, created_at, model, campaign, run_name, llp_pid,
                    cross_section, seed, masses_json, scan_params_json, scan_widths_json,
                    source_metadata_json, selection_config_json, run_config_json,
                    pipeline_options_json, extra_metadata_json, n_cuts
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    result_id,
                    event_id,
                    event_metadata.get("event_hash") or event_metadata.get("run_hash"),
                    event_metadata.get("bundle_sha256") or event_metadata.get("sample_bundle_sha256"),
                    signature,
                    analysis_name,
                    dt.datetime.now().isoformat(),
                    event_metadata.get("model"),
                    event_metadata.get("campaign"),
                    event_metadata.get("run_name"),
                    int(event_metadata["llp_pid"]) if event_metadata.get("llp_pid") is not None else None,
                    float(event_metadata["cross_section"]) if event_metadata.get("cross_section") is not None else None,
                    int(event_metadata["seed"]) if event_metadata.get("seed") is not None else None,
                    _json_dumps(masses),
                    _json_dumps(scan_params),
                    _json_dumps(scan_widths),
                    _json_dumps(event_metadata),
                    _json_dumps(selection_config),
                    _json_dumps(run_config),
                    _json_dumps(pipeline_options),
                    _json_dumps(extra_metadata or {}),
                    len(numeric_cuts),
                ),
            )
            conn.executemany(
                """
                INSERT INTO selection_cuts(
                    result_id, cut_order, cut_name, cut_value, value_type, weighted
                ) VALUES (?,?,?,?,?,?)
                """,
                [(result_id, *cut) for cut in numeric_cuts],
            )
        return result_id


class SelectionResultsAccessor:
    """Query, inspect, and export a selection-results SQLite database."""

    def __init__(self, db: SelectionResultsDatabaseManager | str) -> None:
        self.db = db if isinstance(db, SelectionResultsDatabaseManager) else SelectionResultsDatabaseManager(str(db))

    def query(
        self,
        *,
        model: Optional[str] = None,
        campaign: Optional[str] = None,
        campaign_like: Optional[str] = None,
        run_name: Optional[str] = None,
        event_id: Optional[str] = None,
        event_hash: Optional[str] = None,
        bundle_sha256: Optional[str] = None,
        analysis_name: Optional[str] = None,
        selection_hash: Optional[str] = None,
        llp_pid: Optional[int] = None,
        scan_params: Optional[Mapping[str, Any]] = None,
        scan_widths: Optional[Mapping[str, Any]] = None,
        masses: Optional[Mapping[Any, Any]] = None,
        cut_name: Optional[str] = None,
        cut_min: Optional[float] = None,
        cut_max: Optional[float] = None,
        where: str = "",
        params: Sequence[Any] = (),
        limit: Optional[int] = None,
    ) -> List[sqlite3.Row]:
        """Return result rows matching metadata, JSON-parameter, and cut filters."""
        sql = "SELECT r.* FROM selection_results r WHERE 1=1"
        args: List[Any] = []
        for column, value in (
            ("model", model),
            ("campaign", campaign),
            ("run_name", run_name),
            ("event_id", event_id),
            ("event_hash", event_hash),
            ("bundle_sha256", bundle_sha256),
            ("analysis_name", analysis_name),
            ("selection_hash", selection_hash),
        ):
            if value is not None:
                sql += f" AND r.{column}=?"
                args.append(value)
        if campaign_like is not None:
            sql += " AND r.campaign LIKE ?"
            args.append(campaign_like)
        if llp_pid is not None:
            sql += " AND r.llp_pid=?"
            args.append(int(llp_pid))

        for column, filters in (
            ("scan_params_json", scan_params),
            ("scan_widths_json", scan_widths),
            ("masses_json", masses),
        ):
            for key, value in (filters or {}).items():
                sql += f" AND json_extract(r.{column}, ?) = ?"
                args.extend((_json_path(key), value))

        if cut_name is not None:
            sql += (
                " AND EXISTS (SELECT 1 FROM selection_cuts c "
                "WHERE c.result_id=r.result_id AND c.cut_name=?"
            )
            args.append(cut_name)
            if cut_min is not None:
                sql += " AND c.cut_value>=?"
                args.append(float(cut_min))
            if cut_max is not None:
                sql += " AND c.cut_value<=?"
                args.append(float(cut_max))
            sql += ")"
        elif cut_min is not None or cut_max is not None:
            raise ValueError("cut_min/cut_max require cut_name")

        if where:
            sql += f" AND ({where})"
            args.extend(params)
        sql += " ORDER BY r.created_at DESC"
        if limit is not None:
            sql += " LIMIT ?"
            args.append(int(limit))
        with self.db._conn() as conn:
            return list(conn.execute(sql, tuple(args)))

    def get_cutflow(self, result_id: str, *, preserve_types: bool = True) -> Dict[str, float | int | bool]:
        """Return the ordered cut-flow dictionary for one persisted result."""
        with self.db._conn() as conn:
            rows = conn.execute(
                """
                SELECT cut_name, cut_value, value_type
                FROM selection_cuts WHERE result_id=? ORDER BY cut_order
                """,
                (result_id,),
            ).fetchall()
        out: Dict[str, float | int | bool] = {}
        for row in rows:
            value: float | int | bool = float(row["cut_value"])
            if preserve_types and row["value_type"] == "int":
                value = int(round(float(value)))
            elif preserve_types and row["value_type"] == "bool":
                value = bool(round(float(value)))
            out[str(row["cut_name"])] = value
        return out

    def get_result(self, result_id: str, *, include_cuts: bool = True) -> Optional[Dict[str, Any]]:
        """Return one decoded result row, optionally including its cut flow."""
        with self.db._conn() as conn:
            row = conn.execute("SELECT * FROM selection_results WHERE result_id=?", (result_id,)).fetchone()
        if row is None:
            return None
        out = self._decode_row(row)
        if include_cuts:
            out["cutFlow"] = self.get_cutflow(result_id)
        return out

    @staticmethod
    def _decode_row(row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        for column, key in (
            ("masses_json", "masses"),
            ("scan_params_json", "scan_params"),
            ("scan_widths_json", "scan_widths"),
            ("source_metadata_json", "source_metadata"),
            ("selection_config_json", "selection_config"),
            ("run_config_json", "run_config"),
            ("pipeline_options_json", "pipeline_options"),
            ("extra_metadata_json", "extra_metadata"),
        ):
            item[key] = _loads(item.get(column), {})
        return item

    def to_dataframe(
        self,
        *,
        include_cuts: bool = True,
        expand_physics_metadata: bool = True,
        **filters: Any,
    ):
        """Return query results as a wide pandas DataFrame.

        Cut names become columns.  When ``expand_physics_metadata`` is true,
        masses, scan parameters, and widths are additionally flattened as
        ``mass:<name>``, ``param:<name>``, and ``width:<name>`` columns.
        """
        if pd is None:
            raise RuntimeError("pandas is required for to_dataframe()")
        rows = self.query(**filters)
        records: List[Dict[str, Any]] = []
        for row in rows:
            decoded = self._decode_row(row)
            record = {
                key: value
                for key, value in decoded.items()
                if not key.endswith("_json")
                and key not in {"source_metadata", "selection_config", "run_config", "pipeline_options", "extra_metadata", "masses", "scan_params", "scan_widths"}
            }
            if expand_physics_metadata:
                for prefix, values in (
                    ("mass", decoded.get("masses") or {}),
                    ("param", decoded.get("scan_params") or {}),
                    ("width", decoded.get("scan_widths") or {}),
                ):
                    for key, value in values.items():
                        record[f"{prefix}:{key}"] = value
            if include_cuts:
                record.update(self.get_cutflow(str(row["result_id"])))
            records.append(record)
        return pd.DataFrame.from_records(records)

    def export_csv(self, output_path: str | os.PathLike[str], **filters: Any) -> str:
        """Export a wide query result to one CSV file and return its path."""
        if pd is None:
            raise RuntimeError("pandas is required for export_csv()")
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.to_dataframe(**filters).to_csv(path, index=False)
        return str(path)

    def list_models(self) -> List[Dict[str, Any]]:
        """Return model names and stored-result counts."""
        with self.db._conn() as conn:
            rows = conn.execute(
                "SELECT model, COUNT(*) AS n_results FROM selection_results GROUP BY model ORDER BY n_results DESC, model"
            ).fetchall()
        return [dict(row) for row in rows]

    def list_campaigns(self) -> List[Dict[str, Any]]:
        """Return campaign labels and stored-result counts."""
        with self.db._conn() as conn:
            rows = conn.execute(
                """
                SELECT campaign, COUNT(*) AS n_results
                FROM selection_results
                WHERE campaign IS NOT NULL AND TRIM(campaign)<>''
                GROUP BY campaign ORDER BY n_results DESC, campaign
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_analyses(self) -> List[Dict[str, Any]]:
        """Return analysis labels, configuration signatures, and result counts."""
        with self.db._conn() as conn:
            rows = conn.execute(
                """
                SELECT analysis_name, selection_hash, COUNT(*) AS n_results,
                       MIN(created_at) AS first_result, MAX(created_at) AS last_result
                FROM selection_results
                GROUP BY analysis_name, selection_hash
                ORDER BY last_result DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]
