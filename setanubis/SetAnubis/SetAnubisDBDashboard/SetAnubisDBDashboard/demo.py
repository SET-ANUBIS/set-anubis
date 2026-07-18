"""Create a small, real EventDatabase workspace for the dashboard landing view."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import pickle
import shutil
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from SetAnubis.core.DataBase.domain.EventDatabaseManager import EventDatabaseManager

_DEMO_VERSION = "1"
_EVENT_ID = "setanubis-demo-hnl-r5"


@dataclass(frozen=True)
class DemoWorkspace:
    """Paths to the materialised demonstration database and storage tree."""

    root: Path
    database: Path
    storage: Path
    events_root: Path


_DEMO_BANNER = """<slha>
BLOCK MASS
  9900012  5.000000e+00  # N1 demonstration mass [GeV]
BLOCK QNUMBERS 9900012 # N1
  1  0  # 3 times electric charge
  2  2  # number of spin states
  3  1  # colour representation
  4  0  # self conjugate
DECAY 9900012  1.000000e-15
  5.000000e-01  2  11 -24  # e- W+
  5.000000e-01  2 -11 24  # e+ W-
</slha>
"""


def _resource(name: str):
    return files("SetAnubis.examples.Selection").joinpath("InputFiles", name)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_metadata(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rb") as stream:
        payload = pickle.load(stream)
    frames: dict[str, dict[str, int]] = {}
    for name, dataframe in payload.items():
        frames[str(name)] = {
            "rows": int(len(dataframe)),
            "columns": int(len(dataframe.columns)),
            "memory_bytes": int(dataframe.memory_usage(index=True, deep=True).sum()),
        }
    return {
        "format": "pickle_gzip",
        "stage": "selection_ready",
        "frames": frames,
        "source": "packaged CPC R5 HNL benchmark",
    }


def _copy_resource(name: str, target: Path) -> None:
    with as_file(_resource(name)) as source:
        shutil.copy2(source, target)


def _record_blob(storage: Path, source: Path) -> tuple[str, int, Path]:
    sha = _sha256(source)
    cas_path = storage / "cas" / sha[:2] / sha[2:4] / sha
    cas_path.parent.mkdir(parents=True, exist_ok=True)
    if not cas_path.exists():
        shutil.copy2(source, cas_path)
    return sha, source.stat().st_size, cas_path


def ensure_demo_workspace() -> DemoWorkspace:
    """Materialise the packaged HNL benchmark as a read-only dashboard example."""
    root = Path(
        os.environ.get(
            "SETANUBIS_DB_DEMO_CACHE",
            Path(tempfile.gettempdir()) / "setanubis-db-dashboard-demo-v1",
        )
    ).expanduser()
    database = root / "EventsDatabase.db"
    storage = root / "EventsStorage"
    events_root = root / "Events"
    marker = root / ".demo-version"

    if marker.exists() and marker.read_text(encoding="utf-8").strip() == _DEMO_VERSION and database.exists():
        return DemoWorkspace(root, database, storage, events_root)

    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    storage.mkdir(parents=True, exist_ok=True)
    events_root.mkdir(parents=True, exist_ok=True)

    source_hepmc = root / "hnl_selection_cutflow.hepmc.gz"
    source_bundle = root / "hnl_selection_cutflow_bundle.pkl.gz"
    source_manifest = root / "hnl_selection_cutflow_manifest.json"
    _copy_resource(source_hepmc.name, source_hepmc)
    _copy_resource(source_bundle.name, source_bundle)
    _copy_resource(source_manifest.name, source_manifest)

    EventDatabaseManager(str(database), str(storage))
    hepmc_sha, hepmc_size, _ = _record_blob(storage, source_hepmc)
    bundle_sha, bundle_size, _ = _record_blob(storage, source_bundle)
    manifest_sha, manifest_size, _ = _record_blob(storage, source_manifest)
    bundle_metadata = _bundle_metadata(source_bundle)
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))

    with closing(sqlite3.connect(database)) as conn:
        conn.execute("INSERT OR IGNORE INTO models(name) VALUES (?)", ("UFO_HNL",))
        model_id = conn.execute("SELECT id FROM models WHERE name=?", ("UFO_HNL",)).fetchone()[0]
        conn.execute(
            """
            INSERT OR REPLACE INTO events (
                id, model_id, date_added, is_decayed, cross_section, path,
                lhe_sha256, hepmc_sha256, masses_json, seed, run_hash,
                decay_info_json, banner_text, run_name, scan_params_json,
                scan_widths_json, sample_bundle_sha256, sample_bundle_format,
                bundle_metadata_json, unknown_pids_json, llp_pid, pt_min_cfg_json,
                madgraph_metadata_json, pre_decay_run_name, source_hepmc_filename,
                source_hepmc_size_bytes, decayed_run_dir_size_bytes,
                pre_decay_run_dir_size_bytes, original_runs_total_size_bytes,
                stored_bundle_size_bytes, storage_metadata_json,
                sample_bundle_stage, bundle_processing_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                _EVENT_ID,
                model_id,
                "2026-07-18T00:00:00+00:00",
                1,
                None,
                "package://SetAnubis.examples.Selection/InputFiles",
                None,
                hepmc_sha,
                json.dumps({"9900012": 5.0}),
                1,
                "demo-r5-selection-benchmark",
                json.dumps({"description": "Illustrative HNL decay channels for dashboard inspection."}),
                _DEMO_BANNER,
                "R5_selection_benchmark",
                json.dumps({"benchmark_events": int(manifest.get("event_count", 7)), "llp_mass_GeV": 5.0}),
                json.dumps({"9900012": 1.0e-15}),
                bundle_sha,
                "pickle_gzip",
                json.dumps(bundle_metadata),
                json.dumps([]),
                9900012,
                json.dumps({"chargedTrack": 5.0, "jet": 15.0}),
                json.dumps({
                    "origin": "packaged CPC reproducibility input",
                    "generator_record": source_hepmc.name,
                    "selection_scenario": "R5_selection",
                }),
                None,
                source_hepmc.name,
                hepmc_size,
                None,
                None,
                None,
                bundle_size,
                json.dumps({
                    "comparison": {
                        "source_hepmc_size_bytes": hepmc_size,
                        "stored_bundle_size_bytes": bundle_size,
                        "bundle_over_source_hepmc": bundle_size / hepmc_size if hepmc_size else None,
                    },
                    "note": "Demonstration data materialised from packaged SET-ANUBIS resources.",
                }),
                "selection_ready",
                json.dumps({"phi_fold": False, "jets": True, "isolation": True}),
            ),
        )
        artifacts = [
            ("hepmc_gz", hepmc_sha, source_hepmc.name, hepmc_size),
            ("sample_bundle", bundle_sha, source_bundle.name, bundle_size),
            ("selection_manifest", manifest_sha, source_manifest.name, manifest_size),
        ]
        for kind, sha, filename, size in artifacts:
            conn.execute(
                "INSERT OR REPLACE INTO artifacts(id,event_id,kind,sha256,filename,size_bytes) VALUES (?,?,?,?,?,?)",
                (f"{_EVENT_ID}-{kind}", _EVENT_ID, kind, sha, filename, size),
            )
        for sha, size in [(hepmc_sha, hepmc_size), (bundle_sha, bundle_size), (manifest_sha, manifest_size)]:
            conn.execute(
                "INSERT OR REPLACE INTO cas_blobs(sha256,size_bytes,refcount) VALUES (?,?,1)",
                (sha, size),
            )
        conn.commit()

    marker.write_text(_DEMO_VERSION, encoding="utf-8")
    return DemoWorkspace(root, database, storage, events_root)
