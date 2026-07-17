import importlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .formatting import safe_ratio


def _candidate_modules() -> List[str]:
    return [
        "setanubis.SetAnubis.core.DataBase.domain.EventDatabaseManager",
        "SetAnubis.core.DataBase.domain.EventDatabaseManager",
        "EventDatabaseManager",
    ]


def _candidate_manager_paths() -> List[Path]:
    """Find EventDatabaseManager.py without requiring PYTHONPATH magic.

    This covers the common layouts:
      - launched from the repository root: ./setanubis/SetAnubis/...
      - launched from inside setanubis/SetAnubis
      - dashboard package copied under setanubis/SetAnubis/SetAnubisDBDashboard
      - explicit SETANUBIS_DB_MANAGER_PATH override
    """
    rels = [
        Path("setanubis/SetAnubis/core/DataBase/domain/EventDatabaseManager.py"),
        Path("SetAnubis/core/DataBase/domain/EventDatabaseManager.py"),
        Path("core/DataBase/domain/EventDatabaseManager.py"),
        Path("EventDatabaseManager.py"),
    ]

    roots: List[Path] = []
    cwd = Path.cwd().resolve()
    roots.extend([cwd, *cwd.parents])

    here = Path(__file__).resolve()
    roots.extend([here.parent, *here.parents])

    out: List[Path] = []
    extra = os.environ.get("SETANUBIS_DB_MANAGER_PATH")
    if extra:
        out.append(Path(extra).expanduser().resolve())

    seen = set()
    for root in roots:
        for rel in rels:
            path = (root / rel).resolve()
            if path in seen:
                continue
            seen.add(path)
            if path.exists():
                out.append(path)
    return out


def _load_module_from_path(path: Path):
    spec = importlib.util.spec_from_file_location("EventDatabaseManager", str(path))
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules["EventDatabaseManager"] = module
        spec.loader.exec_module(module)
        return module
    raise ImportError(f"Impossible de charger EventDatabaseManager depuis {path}")


def load_database_module():
    last_exc = None

    # 1) Normal Python imports, when the repo root/package is already on PYTHONPATH.
    for name in _candidate_modules():
        try:
            return importlib.import_module(name)
        except Exception as exc:
            last_exc = exc

    # 2) Direct file loading fallback, robust for the SetAnubis repo layout.
    tried_paths = []
    for path in _candidate_manager_paths():
        tried_paths.append(str(path))
        try:
            return _load_module_from_path(path)
        except Exception as exc:
            last_exc = exc

    msg = (
        "Could not import EventDatabaseManager. Run from the repository root, "
        "or set SETANUBIS_DB_MANAGER_PATH=/path/to/EventDatabaseManager.py."
    )
    if tried_paths:
        msg += " Paths checked: " + "; ".join(tried_paths)
    raise ImportError(msg) from last_exc


def make_accessor(db_path: str, storage_dir: str):
    mod = load_database_module()
    manager_cls = getattr(mod, "EventDatabaseManager", None) or getattr(
        mod, "EventDataBaseManager", None
    )
    accessor_cls = getattr(mod, "EventAccessor")
    if manager_cls is None:
        raise AttributeError(
            "EventDatabaseManager/EventDataBaseManager was not found in "
            "EventDatabaseManager"
        )
    return accessor_cls(manager_cls(db_path, storage_dir))


def _loads(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    try:
        if hasattr(row, "keys") and key in row.keys():
            return row[key]
    except Exception:
        pass
    try:
        return row.get(key, default)
    except Exception:
        return default


def ensure_dashboard_schema(db_path: str, storage_dir: str) -> None:
    """Opening the manager triggers migrations in EventDatabaseManager."""
    make_accessor(db_path, storage_dir)


def load_payload(
    db_path: str,
    storage_dir: str,
    *,
    model: Optional[str] = None,
    llp_pid: Optional[int] = None,
    has_bundle: Optional[bool] = None,
    limit: Optional[int] = 500,
    include_particles: bool = True,
) -> Dict[str, Any]:
    acc = make_accessor(db_path, storage_dir)

    if hasattr(acc, "storage_stats"):
        storage = acc.storage_stats()
    else:
        storage = _fallback_storage_stats(db_path)

    if hasattr(acc, "list_models"):
        models = acc.list_models()
    else:
        models = []

    if hasattr(acc, "events_table"):
        events = acc.events_table(model=model, llp_pid=llp_pid, has_bundle=has_bundle, limit=limit, include_json=True)
    else:
        rows = acc.query(model=model, llp_pid=llp_pid, has_bundle=has_bundle)
        events = [dict(r) for r in (rows[:limit] if limit else rows)]

    particles = []
    if include_particles and hasattr(acc, "list_particles"):
        try:
            particles = acc.list_particles(model=model, include_decays=False)
        except Exception:
            particles = []

    frame_summary = {}
    if hasattr(acc, "bundle_frame_summary"):
        try:
            frame_summary = acc.bundle_frame_summary()
        except Exception:
            frame_summary = {}
    if not frame_summary:
        frame_summary = storage.get("bundle_frames") or {}

    artifacts = storage.get("artifacts_by_kind") or []

    return {
        "db_path": db_path,
        "storage_dir": storage_dir,
        "filters": {"model": model, "llp_pid": llp_pid, "has_bundle": has_bundle, "limit": limit},
        "storage": storage,
        "models": models,
        "events": events,
        "particles": particles,
        "bundle_frames": frame_summary,
        "artifacts": artifacts,
    }


def _fallback_storage_stats(db_path: str) -> Dict[str, Any]:
    out = {"events": 0, "models": 0, "cas_blobs": 0, "cas_size_bytes": 0}
    if not os.path.exists(db_path):
        return out
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for key, sql in [
            ("events", "SELECT COUNT(*) AS n FROM events"),
            ("models", "SELECT COUNT(*) AS n FROM models"),
            ("cas_blobs", "SELECT COUNT(*) AS n FROM cas_blobs"),
        ]:
            try:
                out[key] = int(conn.execute(sql).fetchone()["n"] or 0)
            except Exception:
                pass
        try:
            out["cas_size_bytes"] = int(conn.execute("SELECT COALESCE(SUM(size_bytes),0) AS n FROM cas_blobs").fetchone()["n"] or 0)
        except Exception:
            pass
    return out


def refresh_storage_metadata(
    db_path: str,
    storage_dir: str,
    events_root: str,
    *,
    dry_run: bool = False,
    event_ids: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    acc = make_accessor(db_path, storage_dir)
    if not hasattr(acc, "refresh_storage_metadata_from_events_root"):
        raise RuntimeError("EventDatabaseManager does not yet provide refresh_storage_metadata_from_events_root")
    return acc.refresh_storage_metadata_from_events_root(events_root, event_ids=event_ids, dry_run=dry_run)


def get_event_detail(db_path: str, storage_dir: str, event_id: str) -> Dict[str, Any]:
    acc = make_accessor(db_path, storage_dir)
    ev = acc.get_event(event_id)
    if not ev:
        return {}
    payload = ev.__dict__.copy() if hasattr(ev, "__dict__") else dict(ev)
    for field in [
        "masses_json", "decay_info_json", "scan_params_json", "scan_widths_json", "bundle_metadata_json",
        "unknown_pids_json", "pt_min_cfg_json", "madgraph_metadata_json", "storage_metadata_json",
    ]:
        if field in payload:
            payload[field.replace("_json", "")] = _loads(payload.get(field), {})
    try:
        payload["artifacts"] = [dict(a) for a in acc.get_artifacts(event_id)]
    except Exception:
        payload["artifacts"] = []
    try:
        payload["storage_metadata"] = acc.get_storage_metadata(event_id)
    except Exception:
        pass
    try:
        payload["madgraph_metadata"] = acc.get_madgraph_metadata(event_id)
    except Exception:
        pass
    try:
        payload["bundle_metadata"] = acc.get_bundle_metadata(event_id)
    except Exception:
        pass
    return payload


def get_particle_detail(
    db_path: str,
    storage_dir: str,
    pdg: int,
    *,
    model: Optional[str] = None,
    event_id: Optional[str] = None,
    max_channels: int = 50,
) -> Dict[str, Any]:
    acc = make_accessor(db_path, storage_dir)
    if hasattr(acc, "get_particle_info"):
        info = acc.get_particle_info(pdg, model=model, event_id=event_id, max_channels=max_channels)
        return info or {}
    return {}


def recompute_payload_storage_rollups(payload: Dict[str, Any]) -> Dict[str, Any]:
    events = payload.get("events") or []
    storage = dict(payload.get("storage") or {})
    source_hepmc = sum(int(e.get("source_hepmc_size_bytes") or 0) for e in events)
    original_runs = sum(int(e.get("original_runs_total_size_bytes") or 0) for e in events)
    bundles = sum(int(e.get("stored_bundle_size_bytes") or 0) for e in events)
    if source_hepmc:
        storage["source_hepmc_size_bytes_filtered"] = source_hepmc
        storage["bundle_over_source_hepmc_filtered"] = safe_ratio(bundles, source_hepmc)
    if original_runs:
        storage["original_runs_total_size_bytes_filtered"] = original_runs
        storage["bundle_over_original_runs_filtered"] = safe_ratio(bundles, original_runs)
    if bundles:
        storage["stored_bundle_size_bytes_filtered"] = bundles
    payload["storage_filtered"] = storage
    return payload
