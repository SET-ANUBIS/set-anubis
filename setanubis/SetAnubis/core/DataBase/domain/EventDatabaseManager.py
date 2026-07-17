import datetime as dt
import glob
import gzip
import hashlib
import inspect
import json
import os
import pickle
import re
import shutil
import sqlite3


class _ClosingConnection(sqlite3.Connection):
    """SQLite connection that commits or rolls back and then closes on exit."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

import tempfile
import uuid
import zipfile
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from types import SimpleNamespace

try:
    import pandas as pd
except Exception:
    pd = None

EventId = str
ModelName = str
ArtifactKind = str
Transform = Callable[["EventAccessor", EventId, str], None]
MadGraphFactory = Callable[..., Any]

CAS_DIRNAME = "cas"    
EVENTS_DIRNAME = "events" 

ARTIFACT_SAMPLE_BUNDLE = "sample_bundle"
ARTIFACT_BANNER = "banner"
ARTIFACT_PRE_DECAY_BANNER = "pre_decay_banner"
ARTIFACT_LHE_GZ = "lhe_gz"
ARTIFACT_PRE_DECAY_LHE_GZ = "pre_decay_lhe_gz"
ARTIFACT_HEPMC_GZ = "hepmc_gz"

SAMPLE_BUNDLE_STAGE_LLP_ANALYZER = "llp_analyzer"
SAMPLE_BUNDLE_STAGE_SELECTION_READY = "selection_ready"

# Minimal bundle keys needed by SelectionEnginev2 once jets and isolation are
# already prepared.  chargedFinalStates is kept deliberately: it lets the
# pipeline/engine recompute isolation later if you explicitly remove the
# precomputed minDeltaR columns or change that workflow.  neutralFinalStates,
# finalStates and finalStates_NoLLP are only intermediates for jet/MET building
# and are no longer stored by default.
SELECTION_ENGINE_BUNDLE_KEYS = (
    "LLPs",
    "LLPchildren",
    "finalStatePromptJets",
    "chargedFinalStates",
)

DEFAULT_SELECTION_MIN_PT = {
    "LLP": 0.0,
    "chargedTrack": 5.0,
    "neutralTrack": 5.0,
    "jet": 15.0,
}
DEFAULT_SELECTION_MIN_P = {
    "LLP": 0.1,
    "chargedTrack": 0.1,
    "neutralTrack": 0.1,
    "jet": 0.1,
}

@dataclass
class Event:
    id: EventId
    model: Optional[ModelName]
    date_added: str
    is_decayed: Optional[bool]
    cross_section: Optional[float]
    path: str
    lhe_sha256: Optional[str]
    hepmc_sha256: Optional[str]  
    masses_json: Optional[str]
    seed: Optional[int]
    run_hash: str
    decay_info_json: Optional[str]
    banner_text: Optional[str]
    run_name: Optional[str]
    scan_params_json: Optional[str]
    scan_widths_json: Optional[str]

    sample_bundle_sha256: Optional[str] = None
    sample_bundle_format: Optional[str] = None
    bundle_metadata_json: Optional[str] = None
    unknown_pids_json: Optional[str] = None
    llp_pid: Optional[int] = None
    pt_min_cfg_json: Optional[str] = None
    madgraph_metadata_json: Optional[str] = None
    pre_decay_run_name: Optional[str] = None
    source_hepmc_filename: Optional[str] = None
    source_hepmc_size_bytes: Optional[int] = None
    decayed_run_dir_size_bytes: Optional[int] = None
    pre_decay_run_dir_size_bytes: Optional[int] = None
    original_runs_total_size_bytes: Optional[int] = None
    stored_bundle_size_bytes: Optional[int] = None
    storage_metadata_json: Optional[str] = None
    sample_bundle_stage: Optional[str] = None
    bundle_processing_json: Optional[str] = None


@dataclass(frozen=True)
class BundleBuildConfig:
    """Configuration used to build the stored dict[str, DataFrame]."""

    llp_pid: int
    pt_min_cfg: Dict[str, float]
    bundle_format: str = "pickle_gzip"  # "pickle_gzip", "parquet_zip", or "auto"
    hepmc_frame_options: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class RegenerationResult:
    event_id: str
    run_name: Optional[str]
    output_path: str
    ok: bool
    error: Optional[str] = None


class DataframeBundleIO:
    """Read/write dict[str, pandas.DataFrame] bundles.

    pickle_gzip is the default because it is robust for the object/list columns
    produced by HepmcFrameBuilder (parentIndices, childrenIndices, vertex tuples).
    parquet_zip is attempted when requested; if pyarrow/fastparquet or object columns
    fail, `auto` falls back to pickle_gzip.
    """

    PICKLE_GZIP = "pickle_gzip"
    PARQUET_ZIP = "parquet_zip"
    AUTO = "auto"

    @classmethod
    def save_bundle(
        cls,
        bundle: Dict[str, "pd.DataFrame"],
        output_dir: str,
        basename: str,
        requested_format: str = PICKLE_GZIP,
        metadata_extra: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        if pd is None:
            raise RuntimeError("pandas is required to save dataframe bundles")
        os.makedirs(output_dir, exist_ok=True)
        fmt = requested_format or cls.PICKLE_GZIP
        if fmt not in {cls.PICKLE_GZIP, cls.PARQUET_ZIP, cls.AUTO}:
            raise ValueError(f"Unknown bundle format: {fmt}")

        metadata = cls._bundle_metadata(bundle)
        if metadata_extra:
            metadata.update(metadata_extra)
        if fmt in {cls.PARQUET_ZIP, cls.AUTO}:
            try:
                path = os.path.join(output_dir, f"{basename}.parquet.zip")
                cls._save_parquet_zip(bundle, path, metadata)
                metadata["storage_format"] = cls.PARQUET_ZIP
                return path, cls.PARQUET_ZIP, metadata
            except Exception as exc:
                if fmt == cls.PARQUET_ZIP:
                    raise
                metadata["parquet_fallback_reason"] = repr(exc)

        path = os.path.join(output_dir, f"{basename}.pkl.gz")
        cls._save_pickle_gzip(bundle, path, metadata)
        metadata["storage_format"] = cls.PICKLE_GZIP
        return path, cls.PICKLE_GZIP, metadata

    @classmethod
    def load_bundle(cls, path: str, fmt: Optional[str] = None) -> Dict[str, "pd.DataFrame"]:
        if pd is None:
            raise RuntimeError("pandas is required to load dataframe bundles")
        fmt = fmt or cls._guess_format(path)
        if fmt == cls.PICKLE_GZIP:
            with gzip.open(path, "rb") as f:
                payload = pickle.load(f)
            if isinstance(payload, dict) and "bundle" in payload:
                return payload["bundle"]
            return payload
        if fmt == cls.PARQUET_ZIP:
            return cls._load_parquet_zip(path)
        raise ValueError(f"Unknown bundle format: {fmt}")

    @staticmethod
    def _guess_format(path: str) -> str:
        if path.endswith(".parquet.zip"):
            return DataframeBundleIO.PARQUET_ZIP
        return DataframeBundleIO.PICKLE_GZIP

    @staticmethod
    def _bundle_metadata(bundle: Dict[str, "pd.DataFrame"]) -> Dict[str, Any]:
        frames = {}
        for key, df in bundle.items():
            frames[key] = {
                "rows": int(len(df)),
                "columns": list(map(str, df.columns)),
                "memory_bytes": int(df.memory_usage(deep=True).sum()) if hasattr(df, "memory_usage") else None,
            }
        return {
            "created_at": dt.datetime.now().isoformat(),
            "frames": frames,
            "n_frames": len(frames),
        }

    @staticmethod
    def _save_pickle_gzip(bundle: Dict[str, "pd.DataFrame"], path: str, metadata: Dict[str, Any]) -> None:
        payload = {"metadata": metadata, "bundle": bundle}
        with gzip.open(path, "wb", compresslevel=5) as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _save_parquet_zip(bundle: Dict[str, "pd.DataFrame"], path: str, metadata: Dict[str, Any]) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = {"metadata": metadata, "frames": {}}
            for key, df in bundle.items():
                safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)
                parquet_name = f"{safe_key}.parquet"
                parquet_path = os.path.join(tmp, parquet_name)
                df.to_parquet(parquet_path, index=True)
                manifest["frames"][key] = parquet_name
            manifest_path = os.path.join(tmp, "manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5) as zf:
                zf.write(manifest_path, "manifest.json")
                for filename in manifest["frames"].values():
                    zf.write(os.path.join(tmp, filename), filename)

    @staticmethod
    def _load_parquet_zip(path: str) -> Dict[str, "pd.DataFrame"]:
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(tmp)
            with open(os.path.join(tmp, "manifest.json"), "r") as f:
                manifest = json.load(f)
            out = {}
            for key, filename in manifest["frames"].items():
                out[key] = pd.read_parquet(os.path.join(tmp, filename))
            return out


class BannerInfoParser:
    """Utilities to extract dashboard-friendly information from MadGraph/LHE banners."""

    @staticmethod
    def _to_number(value: str) -> Any:
        try:
            if re.search(r"[.eE]", value):
                return float(value)
            return int(value)
        except Exception:
            try:
                return float(value)
            except Exception:
                return value

    @staticmethod
    def _extract_tag(text: str, tag: str) -> Optional[str]:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text or "", re.S | re.I)
        return m.group(1).strip() if m else None

    @classmethod
    def generation_info(cls, banner_text: str) -> Dict[str, Any]:
        info_text = cls._extract_tag(banner_text, "MGGenerationInfo") or ""
        proc_text = cls._extract_tag(banner_text, "MGProcCard") or cls._extract_tag(banner_text, "MG5ProcCard") or ""
        out: Dict[str, Any] = {
            "mg_version": (cls._extract_tag(banner_text, "MGVersion") or "").strip() or None,
            "number_of_events": None,
            "integrated_weight_pb": None,
            "process": None,
        }
        m = re.search(r"Number of Events\s*:\s*(\d+)", info_text, re.I)
        if m:
            out["number_of_events"] = int(m.group(1))
        m = re.search(r"Integrated weight \(pb\)\s*:\s*([\d.eE+\-]+)", info_text, re.I)
        if m:
            out["integrated_weight_pb"] = float(m.group(1))
        m = re.search(r"^\s*generate\s+(.+)$", proc_text, re.I | re.M)
        if not m:
            m = re.search(r"^(.+?)\s*#\s*Process\s*$", proc_text, re.I | re.M)
        if m:
            out["process"] = m.group(1).strip()
        return out

    @classmethod
    def mass_entries(cls, banner_text: str) -> Dict[int, Dict[str, Any]]:
        masses: Dict[int, Dict[str, Any]] = {}
        m = re.search(r"BLOCK\s+MASS(.*?)(?:\n\s*BLOCK|\n\s*DECAY|</slha>|$)", banner_text or "", re.S | re.I)
        if not m:
            return masses
        for line in m.group(1).splitlines():
            body, _, comment = line.partition("#")
            parts = body.strip().split()
            if len(parts) >= 2 and parts[0].lstrip("-+").isdigit():
                try:
                    masses[int(parts[0])] = {"mass": float(parts[1]), "mass_comment": comment.strip() or None}
                except ValueError:
                    pass
        return masses

    @classmethod
    def qnumbers(cls, banner_text: str) -> Dict[int, Dict[str, Any]]:
        out: Dict[int, Dict[str, Any]] = {}
        pattern = re.compile(r"BLOCK\s+QNUMBERS\s+([+\-]?\d+)\s*(?:#\s*([^\n]*))?(.*?)(?=\n\s*BLOCK|\n\s*DECAY|</slha>|\Z)", re.S | re.I)
        for m in pattern.finditer(banner_text or ""):
            pdg = int(m.group(1)); name = (m.group(2) or "").strip() or None
            values: Dict[int, Any] = {}; comments: Dict[int, str] = {}
            for line in m.group(3).splitlines():
                body, _, comment = line.partition("#")
                parts = body.strip().split()
                if len(parts) >= 2 and parts[0].lstrip("-+").isdigit():
                    key = int(parts[0]); values[key] = cls._to_number(parts[1]); comments[key] = comment.strip()
            three_charge = values.get(1); spin_states = values.get(2)
            out[pdg] = {
                "pdg": pdg, "name": name,
                "three_charge": three_charge,
                "charge": (float(three_charge)/3.0) if isinstance(three_charge, (int, float)) else None,
                "spin_states": spin_states,
                "spin": ((float(spin_states)-1.0)/2.0) if isinstance(spin_states, (int, float)) and spin_states >= 0 else None,
                "color_rep": values.get(3),
                "particle_antiparticle_distinction": values.get(4),
                "self_conjugate": (values.get(4) == 0) if values.get(4) is not None else None,
                "qnumbers_comments": comments,
            }
        return out

    @classmethod
    def decay_entries(cls, banner_text: str) -> Dict[int, Dict[str, Any]]:
        decays: Dict[int, Dict[str, Any]] = {}
        pattern = re.compile(r"^\s*DECAY\s+([+\-]?\d+)\s+([\d.eE+\-]+)(.*?)(?=^\s*DECAY\s+[+\-]?\d+\s+[\d.eE+\-]+|^\s*BLOCK\s+|</slha>|\Z)", re.S | re.I | re.M)
        for m in pattern.finditer(banner_text or ""):
            pdg = int(m.group(1)); width = float(m.group(2)); channels: List[Dict[str, Any]] = []
            for line in m.group(3).splitlines():
                body, _, comment = line.partition("#")
                parts = body.strip().split()
                if len(parts) < 2:
                    continue
                try:
                    br = float(parts[0]); nda = int(parts[1])
                except Exception:
                    continue
                daughters = []
                for tok in parts[2:2+nda]:
                    try: daughters.append(int(tok))
                    except Exception: pass
                channels.append({"branching_ratio": br, "nda": nda, "daughters": daughters, "comment": comment.strip() or None})
            channels.sort(key=lambda x: float(x.get("branching_ratio") or 0.0), reverse=True)
            decays[pdg] = {"pdg": pdg, "width": width, "channels": channels}
        return decays

    @classmethod
    def particle_catalog(cls, banner_text: str, *, include_decays: bool = True, max_channels: int = 25) -> Dict[str, Any]:
        masses = cls.mass_entries(banner_text); qnums = cls.qnumbers(banner_text); decays = cls.decay_entries(banner_text)
        particles: List[Dict[str, Any]] = []
        for pdg in sorted(set(masses) | set(qnums) | set(decays)):
            item: Dict[str, Any] = {"pdg": pdg}
            item.update(qnums.get(pdg, {})); item.update(masses.get(pdg, {}))
            if pdg in decays:
                item["width"] = decays[pdg].get("width")
                channels = decays[pdg].get("channels", [])
                item["n_decay_channels"] = len(channels)
                if include_decays:
                    item["decay_channels"] = channels[:max_channels]
            else:
                item.setdefault("width", None); item.setdefault("n_decay_channels", 0)
            particles.append(item)
        return {"generation_info": cls.generation_info(banner_text), "particles": particles}


class EventDatabaseManager:
    """SQLite manager with content-addressed storage (CAS).

    New imports do not store the decayed HEPMC by default. They store:
      - a compressed dict[str, DataFrame] after HepmcFrameBuilder + LLPAnalyzer
      - MadGraph metadata/cards/banner/scan information
      - optional LHE artifacts if requested
    """

    def __init__(
        self,
        db_path: str = "db/EventsDatabase.db",
        storage_dir: str = "db/EventsStorage",
        use_hardlinks: bool = False,
    ):
        self.db_path = db_path
        self.storage_dir = storage_dir
        self.use_hardlinks = use_hardlinks
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)) or ".", exist_ok=True)
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self._cas_root, exist_ok=True)
        os.makedirs(self._events_root, exist_ok=True)
        self._init_db()

    @property
    def _cas_root(self) -> str:
        return os.path.join(self.storage_dir, CAS_DIRNAME)

    @property
    def _events_root(self) -> str:
        return os.path.join(self.storage_dir, EVENTS_DIRNAME)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, factory=_ClosingConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS models (
                    id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                );
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    model_id INTEGER REFERENCES models(id) ON DELETE SET NULL,
                    date_added TEXT NOT NULL,
                    is_decayed INTEGER,
                    cross_section REAL,
                    path TEXT NOT NULL,
                    lhe_sha256 TEXT,
                    hepmc_sha256 TEXT,
                    masses_json TEXT,
                    seed INTEGER,
                    run_hash TEXT UNIQUE,
                    decay_info_json TEXT,
                    banner_text TEXT,
                    run_name TEXT,
                    scan_params_json TEXT,
                    scan_widths_json TEXT,
                    sample_bundle_sha256 TEXT,
                    sample_bundle_format TEXT,
                    bundle_metadata_json TEXT,
                    unknown_pids_json TEXT,
                    llp_pid INTEGER,
                    pt_min_cfg_json TEXT,
                    madgraph_metadata_json TEXT,
                    pre_decay_run_name TEXT,
                    source_hepmc_filename TEXT,
                    source_hepmc_size_bytes INTEGER,
                    decayed_run_dir_size_bytes INTEGER,
                    pre_decay_run_dir_size_bytes INTEGER,
                    original_runs_total_size_bytes INTEGER,
                    stored_bundle_size_bytes INTEGER,
                    storage_metadata_json TEXT,
                    sample_bundle_stage TEXT,
                    bundle_processing_json TEXT
                );
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    size_bytes INTEGER,
                    UNIQUE(event_id, kind)
                );
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS cas_blobs (
                    sha256 TEXT PRIMARY KEY,
                    size_bytes INTEGER,
                    refcount INTEGER DEFAULT 0
                );
                """
            )
            self._ensure_event_columns(
                conn,
                {
                    "run_name": "TEXT",
                    "scan_params_json": "TEXT",
                    "scan_widths_json": "TEXT",
                    "sample_bundle_sha256": "TEXT",
                    "sample_bundle_format": "TEXT",
                    "bundle_metadata_json": "TEXT",
                    "unknown_pids_json": "TEXT",
                    "llp_pid": "INTEGER",
                    "pt_min_cfg_json": "TEXT",
                    "madgraph_metadata_json": "TEXT",
                    "pre_decay_run_name": "TEXT",
                    "source_hepmc_filename": "TEXT",
                    "source_hepmc_size_bytes": "INTEGER",
                    "decayed_run_dir_size_bytes": "INTEGER",
                    "pre_decay_run_dir_size_bytes": "INTEGER",
                    "original_runs_total_size_bytes": "INTEGER",
                    "stored_bundle_size_bytes": "INTEGER",
                    "storage_metadata_json": "TEXT",
                    "sample_bundle_stage": "TEXT",
                    "bundle_processing_json": "TEXT",
                },
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_model ON events(model_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_event ON artifacts(event_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_sha ON artifacts(sha256);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_run_name ON events(run_name);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_llp_pid ON events(llp_pid);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_bundle_sha ON events(sample_bundle_sha256);")

    @staticmethod
    def _ensure_event_columns(conn: sqlite3.Connection, columns: Dict[str, str]) -> None:
        cur = conn.execute("PRAGMA table_info(events)")
        existing = {row[1] for row in cur.fetchall()}
        for col, sql_type in columns.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE events ADD COLUMN {col} {sql_type}")

    def _get_or_create_model_id(self, name: Optional[str]) -> Optional[int]:
        if not name:
            return None
        with self._conn() as conn:
            return self._get_or_create_model_id_in_conn(conn, name)

    @staticmethod
    def _get_or_create_model_id_in_conn(conn: sqlite3.Connection, name: str) -> int:
        cur = conn.execute("SELECT id FROM models WHERE name=?", (name,))
        row = cur.fetchone()
        if row:
            return int(row[0])
        cur = conn.execute("INSERT INTO models(name) VALUES (?)", (name,))
        return int(cur.lastrowid)

    def _cas_path(self, sha256: str) -> str:
        return os.path.join(self._cas_root, sha256[:2], sha256)

    def _ensure_cas_dirs(self, sha256: str) -> None:
        os.makedirs(os.path.dirname(self._cas_path(sha256)), exist_ok=True)

    def _ingest_file_to_cas(self, src: str, sha256: Optional[str] = None) -> Tuple[str, int]:
        if sha256 is None:
            sha256 = self._sha256_file(src)
        self._ensure_cas_dirs(sha256)
        dst = self._cas_path(sha256)
        size = os.path.getsize(src)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            try:
                os.chmod(dst, 0o644)
            except Exception:
                pass
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO cas_blobs(sha256, size_bytes, refcount) VALUES(?,?,1) "
                "ON CONFLICT(sha256) DO UPDATE SET refcount=refcount+1;",
                (sha256, size),
            )
        return sha256, size

    @staticmethod
    def _sha256_file(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _link_into_event_folder(self, sha256: str, event_folder: str, filename: str) -> str:
        os.makedirs(event_folder, exist_ok=True)
        cas_file = self._cas_path(sha256)
        target = os.path.join(event_folder, filename)
        if os.path.lexists(target):
            return target
        try:
            if self.use_hardlinks:
                os.link(cas_file, target)
            else:
                rel = os.path.relpath(cas_file, start=event_folder)
                os.symlink(rel, target)
        except (OSError, NotImplementedError):
            shutil.copy2(cas_file, target)
        return target



class EventImporter:
    """Import generator runs into the current event database and CAS.

    The importer extracts scan metadata, optionally builds compact selection
    bundles from HepMC, deduplicates runs by content hash, and records artifacts
    in the database storage managed by :class:`EventDatabaseManager`.
    """

    def __init__(self, db: EventDatabaseManager):
        self.db = db

    def import_from_events_folder(
        self,
        events_folder: str,
        *,
        model: Optional[str] = None,
        neo_manager: Any = None,
        llp_pid: Optional[int] = None,
        pt_min_cfg: Optional[Dict[str, float]] = None,
        bundle_format: str = DataframeBundleIO.PICKLE_GZIP,
        hepmc_frame_options: Optional[Dict[str, Any]] = None,
        selection_ready: bool = True,
        phi_fold: bool = False,
        prune_bundle: bool = True,
        selection_min_pt: Optional[Dict[str, float]] = None,
        selection_min_p: Optional[Dict[str, float]] = None,
        only_decayed: bool = True,
        store_lhe: bool = False,
        store_banners: bool = True,
        include_hepmc: bool = False,
        progress_hook: Optional[Callable[[int], None]] = None,
        max_runs: Optional[int] = None,
    ) -> List[EventId]:
        """Import MadGraph Events/* runs.

        The importer reads decayed HEPMC files, converts them to a dict[str, DataFrame]
        through HepmcFrameBuilder + LLPAnalyzer, and stores the bundle in CAS.

        Args:
            neo_manager: SetAnubisInterface-like object used by HepmcFrameBuilder.
            llp_pid: LLP PDG id required when creating the sample dataframe bundle.
            pt_min_cfg: LLPAnalyzer pT thresholds, e.g. {"chargedTrack": 0.5}.
            only_decayed: if True, skip non-decayed run folders.
            store_lhe: optional legacy storage of LHE files; off by default for lightweight DBs.
            include_hepmc: explicit opt-in legacy behavior. Keep False to avoid storing HEPMC.
            selection_ready: if True, apply optional phi-fold, build jets, attach isolation,
                and store only the compact SelectionEngine-ready frames.
            phi_fold: apply PhiFoldTransform before LLPAnalyzer, matching the SelectionPipeline
                pre-df transform. Existing bundles cannot be phi-folded after the fact; reimport
                from HEPMC when changing this option.
            prune_bundle: if True, store only SELECTION_ENGINE_BUNDLE_KEYS.
            selection_min_pt/selection_min_p: thresholds used for precomputed isolation.
        """
        if not os.path.isdir(events_folder):
            raise FileNotFoundError(events_folder)
        if (neo_manager is None) ^ (llp_pid is None):
            raise ValueError("neo_manager and llp_pid must be provided together to build dataframe bundles")

        scan_map = self._parse_scan_table(events_folder)
        run_folders = [
            os.path.join(events_folder, d)
            for d in os.listdir(events_folder)
            if os.path.isdir(os.path.join(events_folder, d))
        ]
        run_folders = sorted(run_folders)
        pre_decay_map = {
            self._scan_base_key(os.path.basename(r.rstrip(os.sep))): r
            for r in run_folders
            if not self._looks_decayed(r)
        }

        imported: List[EventId] = []
        candidates = [r for r in run_folders if (self._looks_decayed(r) or not only_decayed)]
        if max_runs is not None:
            candidates = candidates[: int(max_runs)]
        for run in candidates:
            ev = self._import_single_run(
                run,
                model=model,
                neo_manager=neo_manager,
                llp_pid=llp_pid,
                pt_min_cfg=pt_min_cfg or {},
                bundle_format=bundle_format,
                hepmc_frame_options=hepmc_frame_options,
                selection_ready=selection_ready,
                phi_fold=phi_fold,
                prune_bundle=prune_bundle,
                selection_min_pt=selection_min_pt,
                selection_min_p=selection_min_p,
                store_lhe=store_lhe,
                store_banners=store_banners,
                include_hepmc=include_hepmc,
                scan_map=scan_map,
                pre_decay_map=pre_decay_map,
                progress_hook=progress_hook,
            )
            if ev:
                imported.append(ev)
        return imported

    def _import_single_run(
        self,
        run_folder: str,
        *,
        model: Optional[str],
        neo_manager: Any,
        llp_pid: Optional[int],
        pt_min_cfg: Dict[str, float],
        bundle_format: str,
        hepmc_frame_options: Optional[Dict[str, Any]],
        selection_ready: bool,
        phi_fold: bool,
        prune_bundle: bool,
        selection_min_pt: Optional[Dict[str, float]],
        selection_min_p: Optional[Dict[str, float]],
        store_lhe: bool,
        store_banners: bool,
        include_hepmc: bool,
        scan_map: Dict[str, Dict[str, Any]],
        pre_decay_map: Dict[str, str],
        progress_hook: Optional[Callable[[int], None]],
    ) -> Optional[EventId]:
        run_name = os.path.basename(run_folder.rstrip(os.sep))
        scan_key = self._scan_base_key(run_name)
        scan_row = (scan_map.get(run_name) or scan_map.get(scan_key) or {}) if scan_map else {}
        cross_from_scan = scan_row.get("cross")
        scan_params = scan_row.get("params", {})
        scan_widths = scan_row.get("widths", {})

        all_files = glob.glob(os.path.join(run_folder, "*"))
        banner_file = self._find_banner_file(run_folder)
        lhe_file = self._find_file(run_folder, r"\.lhe(\.gz)?$")
        hepmc_file = self._find_file(run_folder, r"\.hepmc(\.gz)?$") or self._find_file(run_folder, r"\.hepmc\.gz$")
        if not hepmc_file:
            print(f"Skipping {run_folder}: no HEPMC file found to build dataframe bundle.")
            return None

        pre_decay_folder = pre_decay_map.get(scan_key)
        pre_decay_run_name = os.path.basename(pre_decay_folder.rstrip(os.sep)) if pre_decay_folder else None
        pre_decay_banner_file = self._find_banner_file(pre_decay_folder) if pre_decay_folder else None
        pre_decay_lhe_file = self._find_file(pre_decay_folder, r"\.lhe(\.gz)?$") if pre_decay_folder else None

        source_hepmc_size_bytes = os.path.getsize(hepmc_file) if hepmc_file and os.path.exists(hepmc_file) else None
        decayed_run_dir_size_bytes = self._dir_size(run_folder)
        pre_decay_run_dir_size_bytes = self._dir_size(pre_decay_folder) if pre_decay_folder else None
        original_runs_total_size_bytes = self._sum_unique_directory_sizes([pre_decay_folder, run_folder])

        banner_text = self._read_text(banner_file) if banner_file else ""
        pre_banner_text = self._read_text(pre_decay_banner_file) if pre_decay_banner_file else ""

        cross_banner = self._parse_cross_section(banner_text) or self._parse_cross_section(pre_banner_text)
        masses = self._parse_masses(banner_text) or self._parse_masses(pre_banner_text)
        seed = self._parse_seed(banner_text) or self._parse_seed(pre_banner_text)
        seed_source = "banner"
        if seed is None:
            seed = self._generate_seed()
            seed_source = "generated_by_database_import_missing_in_banner"
        decay_info = self._parse_decay_info(banner_text) or self._parse_decay_info(pre_banner_text)
        detected_model = self._parse_model(banner_text) or self._parse_model(pre_banner_text) or model
        is_decayed = self._looks_decayed(run_folder)
        cross_section = cross_from_scan if cross_from_scan is not None else cross_banner

        madgraph_metadata = self._collect_madgraph_metadata(
            run_folder=run_folder,
            pre_decay_folder=pre_decay_folder,
            scan_row=scan_row,
            seed=seed,
            seed_source=seed_source,
            model=detected_model,
            source_hepmc_filename=os.path.basename(hepmc_file),
        )
        run_hash = self._compute_run_hash(run_folder, pre_decay_folder, madgraph_metadata)
        with self.db._conn() as conn:
            row = conn.execute("SELECT id FROM events WHERE run_hash=?", (run_hash,)).fetchone()
            if row:
                print(f"Run {run_folder} already imported as {row['id']}. Skipping.")
                return None

        event_id = str(uuid.uuid4())
        event_folder = os.path.join(self.db._events_root, event_id)
        os.makedirs(event_folder, exist_ok=True)

        sample_bundle_sha256 = None
        sample_bundle_format = None
        bundle_path: Optional[str] = None
        bundle_size = 0
        bundle_metadata: Optional[Dict[str, Any]] = None
        bundle_processing: Optional[Dict[str, Any]] = None
        sample_bundle_stage = None
        unknown_pids: List[int] = []
        if neo_manager is not None and llp_pid is not None:
            bundle, unknown_pids, bundle_processing = self._build_sample_bundle_from_hepmc(
                hepmc_file,
                neo_manager=neo_manager,
                llp_pid=int(llp_pid),
                pt_min_cfg=pt_min_cfg,
                frame_options=hepmc_frame_options,
                progress_hook=progress_hook,
                selection_ready=selection_ready,
                phi_fold=phi_fold,
                prune_bundle=prune_bundle,
                selection_min_pt=selection_min_pt,
                selection_min_p=selection_min_p,
            )
            sample_bundle_stage = bundle_processing.get("stage") if bundle_processing else SAMPLE_BUNDLE_STAGE_LLP_ANALYZER
            bundle_path, sample_bundle_format, bundle_metadata = DataframeBundleIO.save_bundle(
                bundle,
                output_dir=event_folder,
                basename=f"{run_name}_sampledfs",
                requested_format=bundle_format,
                metadata_extra={"processing": bundle_processing or {}},
            )
            sample_bundle_sha256, bundle_size = self._ingest_to_cas(bundle_path)
            self.db._link_into_event_folder(sample_bundle_sha256, event_folder, os.path.basename(bundle_path))
        elif neo_manager is None and llp_pid is None:
            bundle_size = 0
        else:  # defensive, should have been caught by public method
            raise ValueError("neo_manager and llp_pid must be provided together")

        lhe_sha256 = None
        if store_lhe and lhe_file:
            lhe_sha256, lhe_filename, lhe_size = self._ingest_possibly_gzip(lhe_file, event_folder)
        else:
            lhe_filename = None
            lhe_size = 0

        pre_decay_lhe_sha256 = None
        if store_lhe and pre_decay_lhe_file:
            pre_decay_lhe_sha256, pre_lhe_filename, pre_lhe_size = self._ingest_possibly_gzip(pre_decay_lhe_file, event_folder)
        else:
            pre_lhe_filename = None
            pre_lhe_size = 0

        hepmc_sha256 = None
        if include_hepmc:
            hepmc_sha256, hepmc_filename, hepmc_size = self._ingest_possibly_gzip(hepmc_file, event_folder)
        else:
            hepmc_filename = None
            hepmc_size = 0

        with self.db._conn() as conn:
            model_id = EventDatabaseManager._get_or_create_model_id_in_conn(conn, detected_model) if detected_model else None
            conn.execute(
                """
                INSERT INTO events (
                    id, model_id, date_added, is_decayed, cross_section, path,
                    lhe_sha256, hepmc_sha256, masses_json, seed, run_hash,
                    decay_info_json, banner_text, run_name, scan_params_json, scan_widths_json,
                    sample_bundle_sha256, sample_bundle_format, bundle_metadata_json,
                    unknown_pids_json, llp_pid, pt_min_cfg_json, madgraph_metadata_json,
                    pre_decay_run_name, source_hepmc_filename, sample_bundle_stage, bundle_processing_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    event_id,
                    model_id,
                    dt.datetime.now().isoformat(),
                    int(is_decayed),
                    cross_section,
                    event_folder,
                    lhe_sha256,
                    hepmc_sha256,
                    json.dumps(masses) if masses else None,
                    int(seed) if seed is not None else None,
                    run_hash,
                    json.dumps(decay_info) if decay_info else None,
                    banner_text or None,
                    run_name,
                    json.dumps(scan_params) if scan_params else None,
                    json.dumps(scan_widths) if scan_widths else None,
                    sample_bundle_sha256,
                    sample_bundle_format,
                    json.dumps(bundle_metadata) if bundle_metadata else None,
                    json.dumps(unknown_pids),
                    int(llp_pid) if llp_pid is not None else None,
                    json.dumps(pt_min_cfg) if pt_min_cfg else None,
                    json.dumps(madgraph_metadata),
                    pre_decay_run_name,
                    os.path.basename(hepmc_file),
                    sample_bundle_stage,
                    json.dumps(bundle_processing) if bundle_processing else None,
                ),
            )

        if sample_bundle_sha256:
            self._record_artifact(event_id, ARTIFACT_SAMPLE_BUNDLE, sample_bundle_sha256, os.path.basename(bundle_path), int(bundle_size))
        if lhe_sha256 and lhe_filename:
            self._record_artifact(event_id, ARTIFACT_LHE_GZ, lhe_sha256, lhe_filename, int(lhe_size))
            self.db._link_into_event_folder(lhe_sha256, event_folder, lhe_filename)
        if pre_decay_lhe_sha256 and pre_lhe_filename:
            self._record_artifact(event_id, ARTIFACT_PRE_DECAY_LHE_GZ, pre_decay_lhe_sha256, pre_lhe_filename, int(pre_lhe_size))
            self.db._link_into_event_folder(pre_decay_lhe_sha256, event_folder, pre_lhe_filename)
        if hepmc_sha256 and hepmc_filename:
            self._record_artifact(event_id, ARTIFACT_HEPMC_GZ, hepmc_sha256, hepmc_filename, int(hepmc_size))
            self.db._link_into_event_folder(hepmc_sha256, event_folder, hepmc_filename)
        if store_banners and banner_file:
            sha, size = self._ingest_to_cas(banner_file)
            self._record_artifact(event_id, ARTIFACT_BANNER, sha, os.path.basename(banner_file), size)
            self.db._link_into_event_folder(sha, event_folder, os.path.basename(banner_file))
        if store_banners and pre_decay_banner_file:
            sha, size = self._ingest_to_cas(pre_decay_banner_file)
            self._record_artifact(event_id, ARTIFACT_PRE_DECAY_BANNER, sha, os.path.basename(pre_decay_banner_file), size)
            self.db._link_into_event_folder(sha, event_folder, os.path.basename(pre_decay_banner_file))

        self._update_event_storage_metadata_after_import(
            event_id, run_folder=run_folder, pre_decay_folder=pre_decay_folder,
            hepmc_file=hepmc_file, bundle_path=bundle_path,
            source_hepmc_size_bytes=source_hepmc_size_bytes,
            decayed_run_dir_size_bytes=decayed_run_dir_size_bytes,
            pre_decay_run_dir_size_bytes=pre_decay_run_dir_size_bytes,
            original_runs_total_size_bytes=original_runs_total_size_bytes,
            stored_bundle_size_bytes=int(bundle_size or 0),
            stored_hepmc_size_bytes=int(hepmc_size or 0),
            stored_lhe_size_bytes=int(lhe_size or 0),
            stored_pre_decay_lhe_size_bytes=int(pre_lhe_size or 0),
        )

        print(
            f"Imported event {event_id} "
            f"(run={run_name}, pre_decay={pre_decay_run_name}, model={detected_model}, "
            f"bundle={sample_bundle_format}, stage={sample_bundle_stage}, hepmc_stored={bool(hepmc_sha256)})"
        )
        return event_id


    @staticmethod
    def _dir_size(folder: Optional[str]) -> int:
        if not folder or not os.path.isdir(folder):
            return 0
        total = 0
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    if not os.path.islink(path):
                        total += os.path.getsize(path)
                except OSError:
                    pass
        return int(total)

    @classmethod
    def _sum_unique_directory_sizes(cls, folders: Iterable[Optional[str]]) -> int:
        seen: set[str] = set(); total = 0
        for folder in folders:
            if not folder:
                continue
            real = os.path.realpath(folder)
            if real in seen:
                continue
            seen.add(real); total += cls._dir_size(folder)
        return int(total)

    @staticmethod
    def _safe_ratio(numerator: Optional[int], denominator: Optional[int]) -> Optional[float]:
        if numerator is None or denominator in (None, 0):
            return None
        return float(numerator) / float(denominator)

    @staticmethod
    def _format_bytes(value: Optional[int]) -> Optional[str]:
        if value is None:
            return None
        n = float(value)
        for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
            if abs(n) < 1024.0 or unit == "PB":
                return f"{n:.2f} {unit}" if unit != "B" else f"{int(n)} B"
            n /= 1024.0
        return f"{value} B"

    @classmethod
    def _build_storage_metadata(
        cls, *, run_folder: Optional[str], pre_decay_folder: Optional[str], hepmc_file: Optional[str], bundle_path: Optional[str],
        source_hepmc_size_bytes: Optional[int], decayed_run_dir_size_bytes: Optional[int], pre_decay_run_dir_size_bytes: Optional[int],
        original_runs_total_size_bytes: Optional[int], stored_bundle_size_bytes: Optional[int], stored_hepmc_size_bytes: int = 0,
        stored_lhe_size_bytes: int = 0, stored_pre_decay_lhe_size_bytes: int = 0,
    ) -> Dict[str, Any]:
        bundle_size = int(stored_bundle_size_bytes or 0)
        original_total = int(original_runs_total_size_bytes or 0)
        hepmc_size = int(source_hepmc_size_bytes) if source_hepmc_size_bytes is not None else None
        return {
            "created_at": dt.datetime.now().isoformat(),
            "source": {
                "decayed_run_name": os.path.basename(run_folder.rstrip(os.sep)) if run_folder else None,
                "pre_decay_run_name": os.path.basename(pre_decay_folder.rstrip(os.sep)) if pre_decay_folder else None,
                "hepmc_filename": os.path.basename(hepmc_file) if hepmc_file else None,
                "hepmc_size_bytes": hepmc_size,
                "hepmc_size_human": cls._format_bytes(hepmc_size),
                "decayed_run_dir_size_bytes": int(decayed_run_dir_size_bytes or 0),
                "pre_decay_run_dir_size_bytes": int(pre_decay_run_dir_size_bytes or 0),
                "original_runs_total_size_bytes": original_total,
                "original_runs_total_size_human": cls._format_bytes(original_total),
            },
            "stored": {
                "bundle_filename": os.path.basename(bundle_path) if bundle_path else None,
                "bundle_size_bytes": bundle_size,
                "bundle_size_human": cls._format_bytes(bundle_size),
                "hepmc_size_bytes": int(stored_hepmc_size_bytes or 0),
                "lhe_size_bytes": int(stored_lhe_size_bytes or 0),
                "pre_decay_lhe_size_bytes": int(stored_pre_decay_lhe_size_bytes or 0),
            },
            "comparison": {
                "bundle_over_source_hepmc": cls._safe_ratio(bundle_size, hepmc_size),
                "bundle_over_original_runs": cls._safe_ratio(bundle_size, original_total),
                "saved_vs_source_hepmc_bytes": (hepmc_size - bundle_size) if hepmc_size is not None else None,
                "saved_vs_original_runs_bytes": original_total - bundle_size if original_total else None,
                "saved_vs_original_runs_fraction": (1.0 - (bundle_size / original_total)) if original_total else None,
            },
        }

    def _update_event_storage_metadata_after_import(self, event_id: str, **kwargs: Any) -> None:
        metadata = self._build_storage_metadata(**kwargs)
        with self.db._conn() as conn:
            conn.execute(
                """
                UPDATE events SET source_hepmc_size_bytes=?, decayed_run_dir_size_bytes=?,
                    pre_decay_run_dir_size_bytes=?, original_runs_total_size_bytes=?,
                    stored_bundle_size_bytes=?, storage_metadata_json=?
                WHERE id=?
                """,
                (
                    int(kwargs.get("source_hepmc_size_bytes")) if kwargs.get("source_hepmc_size_bytes") is not None else None,
                    int(kwargs.get("decayed_run_dir_size_bytes") or 0),
                    int(kwargs.get("pre_decay_run_dir_size_bytes")) if kwargs.get("pre_decay_run_dir_size_bytes") is not None else None,
                    int(kwargs.get("original_runs_total_size_bytes") or 0),
                    int(kwargs.get("stored_bundle_size_bytes") or 0),
                    json.dumps(metadata),
                    event_id,
                ),
            )

    @staticmethod
    def _normalise_thresholds(values: Optional[Dict[str, float]], defaults: Dict[str, float]) -> Dict[str, float]:
        out = dict(defaults)
        if values:
            for key, value in values.items():
                if value is not None:
                    out[str(key)] = float(value)
        return out

    @staticmethod
    def _selection_view(min_pt: Dict[str, float], min_p: Dict[str, float]) -> Any:
        """Small SelectionConfig-like object used by IsolationComputer.

        IsolationComputer only reads selection.minPt.{jet,chargedTrack} and
        selection.minP.jet, so we do not need to instantiate a geometry-heavy
        SelectionConfig during database import.
        """
        return SimpleNamespace(
            minPt=SimpleNamespace(**min_pt),
            minP=SimpleNamespace(**min_p),
        )

    @classmethod
    def _prepare_selection_ready_bundle(
        cls,
        bundle: Dict[str, "pd.DataFrame"],
        *,
        llp_pid: int,
        selection_min_pt: Optional[Dict[str, float]],
        selection_min_p: Optional[Dict[str, float]],
        build_jets: bool = True,
        compute_isolation: bool = True,
        prune_bundle: bool = True,
    ) -> Tuple[Dict[str, "pd.DataFrame"], Dict[str, Any]]:
        if pd is None:
            raise RuntimeError("pandas is required to prepare dataframe bundles")

        min_pt = cls._normalise_thresholds(selection_min_pt, DEFAULT_SELECTION_MIN_PT)
        min_p = cls._normalise_thresholds(selection_min_p, DEFAULT_SELECTION_MIN_P)
        out: Dict[str, "pd.DataFrame"] = dict(bundle)

        processing: Dict[str, Any] = {
            "stage": SAMPLE_BUNDLE_STAGE_SELECTION_READY,
            "llp_pid": int(llp_pid),
            "stored_keys_target": list(SELECTION_ENGINE_BUNDLE_KEYS) if prune_bundle else "all",
            "frames_before_processing": sorted(list(bundle.keys())),
            "selection_min_pt": min_pt,
            "selection_min_p": min_p,
            "steps": [],
            "note": (
                "Bundle prepared for SelectionEnginev2: phi-fold is applied before LLPAnalyzer when requested; "
                "jets and minDeltaR isolation are precomputed at import time. If you run through SelectionPipeline, "
                "use the patched pipeline which does not overwrite existing finalStatePromptJets/minDeltaR columns."
            ),
        }

        if build_jets:
            _, createJetDF, _ = cls._load_selection_postprocessors()
            cfs = out.get("chargedFinalStates", pd.DataFrame())
            nfs = out.get("neutralFinalStates", pd.DataFrame())
            event_numbers = set()
            if cfs is not None and not cfs.empty and "eventNumber" in cfs.columns:
                event_numbers.update(int(x) for x in cfs["eventNumber"].dropna().unique().tolist())
            if nfs is not None and not nfs.empty and "eventNumber" in nfs.columns:
                event_numbers.update(int(x) for x in nfs["eventNumber"].dropna().unique().tolist())
            if event_numbers:
                out["finalStatePromptJets"] = createJetDF(sorted(event_numbers), cfs, nfs)
            else:
                out["finalStatePromptJets"] = pd.DataFrame()
            processing["steps"].append({
                "name": "jet_builder",
                "output_key": "finalStatePromptJets",
                "rows": int(len(out.get("finalStatePromptJets", pd.DataFrame()))),
            })

        if compute_isolation:
            _, _, IsolationComputer = cls._load_selection_postprocessors()
            llps = out.get("LLPs", pd.DataFrame())
            if llps is not None and not llps.empty:
                iso = IsolationComputer(selection=cls._selection_view(min_pt, min_p))
                out["LLPs"] = iso.attach_min_delta_r(out)
                rows = int(len(out["LLPs"]))
            else:
                rows = 0
            processing["steps"].append({
                "name": "isolation",
                "llp_key": "LLPs",
                "columns": ["minDeltaR_Jets", "minDeltaR_Tracks"],
                "rows": rows,
            })

        if prune_bundle:
            pruned: Dict[str, "pd.DataFrame"] = {}
            for key in SELECTION_ENGINE_BUNDLE_KEYS:
                pruned[key] = out.get(key, pd.DataFrame())
            out = pruned
            processing["steps"].append({
                "name": "prune_bundle",
                "kept_keys": list(SELECTION_ENGINE_BUNDLE_KEYS),
                "dropped_keys": sorted([k for k in bundle.keys() if k not in SELECTION_ENGINE_BUNDLE_KEYS]),
            })

        processing["frames_after_processing"] = sorted(list(out.keys()))
        processing["frame_rows_after_processing"] = {k: int(len(v)) for k, v in out.items()}
        return out, processing

    def _build_sample_bundle_from_hepmc(
        self,
        hepmc_file: str,
        *,
        neo_manager: Any,
        llp_pid: int,
        pt_min_cfg: Dict[str, float],
        frame_options: Optional[Dict[str, Any]],
        progress_hook: Optional[Callable[[int], None]],
        selection_ready: bool = True,
        phi_fold: bool = False,
        prune_bundle: bool = True,
        selection_min_pt: Optional[Dict[str, float]] = None,
        selection_min_p: Optional[Dict[str, float]] = None,
    ) -> Tuple[Dict[str, "pd.DataFrame"], List[int], Dict[str, Any]]:
        if pd is None:
            raise RuntimeError("pandas is required to build dataframe bundles")
        pyhepmc, HepmcFrameBuilder, HepmcFrameOptions, LLPAnalyzer = self._load_selection_dependencies()
        opt = HepmcFrameOptions(**(frame_options or {}))
        builder = HepmcFrameBuilder(neo_manager=neo_manager, options=opt, progress_hook=progress_hook)
        with pyhepmc.open(hepmc_file) as stream:
            df, unknown_pids = builder.build_from_events(stream)

        processing: Dict[str, Any] = {
            "stage": SAMPLE_BUNDLE_STAGE_LLP_ANALYZER,
            "llp_pid": int(llp_pid),
            "phi_fold": bool(phi_fold),
            "selection_ready": bool(selection_ready),
            "prune_bundle": bool(prune_bundle),
            "hepmc_frame_options": frame_options or {},
            "llp_analyzer_pt_min_cfg": dict(pt_min_cfg or {}),
            "steps": [{"name": "hepmc_frame_builder", "rows": int(len(df))}],
        }

        if phi_fold:
            phi_fold_df, _, _ = self._load_selection_postprocessors()
            df = phi_fold_df(df, int(llp_pid))
            processing["steps"].append({"name": "phi_fold", "llp_pid": int(llp_pid), "rows": int(len(df))})

        analyzer = LLPAnalyzer(df, pt_min_cfg=pt_min_cfg)
        bundle = analyzer.create_sample_dataframes(llp_pid)
        processing["steps"].append({
            "name": "llp_analyzer",
            "frames": sorted(list(bundle.keys())),
            "frame_rows": {k: int(len(v)) for k, v in bundle.items()},
        })

        if selection_ready:
            bundle, ready_processing = self._prepare_selection_ready_bundle(
                bundle,
                llp_pid=int(llp_pid),
                selection_min_pt=selection_min_pt,
                selection_min_p=selection_min_p,
                build_jets=True,
                compute_isolation=True,
                prune_bundle=prune_bundle,
            )
            ready_processing["pre_steps"] = processing["steps"]
            ready_processing["phi_fold"] = bool(phi_fold)
            ready_processing["hepmc_frame_options"] = frame_options or {}
            ready_processing["llp_analyzer_pt_min_cfg"] = dict(pt_min_cfg or {})
            processing = ready_processing
        else:
            processing["frames_after_processing"] = sorted(list(bundle.keys()))
            processing["frame_rows_after_processing"] = {k: int(len(v)) for k, v in bundle.items()}

        return bundle, list(map(int, unknown_pids)), processing

    @staticmethod
    def _load_selection_dependencies():
        try:
            import pyhepmc
        except Exception as exc:
            raise RuntimeError("pyhepmc is required to import HEPMC files") from exc
        try:
            from SetAnubis.core.Selection.domain.HepMCFrameBuilder import HepmcFrameBuilder, HepmcFrameOptions
        except Exception:
            from HepMCFrameBuilder import HepmcFrameBuilder, HepmcFrameOptions  # type: ignore
        try:
            from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer
        except Exception:
            from LLPAnalyzer import LLPAnalyzer  # type: ignore
        return pyhepmc, HepmcFrameBuilder, HepmcFrameOptions, LLPAnalyzer

    @staticmethod
    def _load_selection_postprocessors():
        try:
            from SetAnubis.core.Selection.domain.PhiFoldTransform import phi_fold_df
        except Exception:
            try:
                from PhiFoldTransform import phi_fold_df  # type: ignore
            except Exception as exc:
                raise RuntimeError("PhiFoldTransform.phi_fold_df is required when phi_fold=True") from exc
        try:
            from SetAnubis.core.Selection.domain.JetBuilder import createJetDF
        except Exception:
            try:
                from JetBuilder import createJetDF  # type: ignore
            except Exception as exc:
                raise RuntimeError("JetBuilder.createJetDF is required to prepare selection-ready bundles") from exc
        try:
            from SetAnubis.core.Selection.domain.isolation import IsolationComputer
        except Exception:
            try:
                from isolation import IsolationComputer  # type: ignore
            except Exception as exc:
                raise RuntimeError("isolation.IsolationComputer is required to prepare selection-ready bundles") from exc
        return phi_fold_df, createJetDF, IsolationComputer

    @staticmethod
    def _looks_decayed(run_folder: str) -> bool:
        name = os.path.basename(run_folder.rstrip(os.sep))
        if re.search(r"decay|decayed|madspin", name, re.I):
            return True
        for p in glob.glob(os.path.join(run_folder, "*")):
            if re.search(r"decay|decayed|madspin", os.path.basename(p), re.I):
                return True
        return False

    @staticmethod
    def _scan_base_key(run_name_or_folder: str) -> str:
        name = os.path.basename(run_name_or_folder.rstrip(os.sep))
        return re.sub(r"(_|-)?decayed.*$", "", name, flags=re.I)

    @staticmethod
    def _find_file(folder: Optional[str], pattern: str) -> Optional[str]:
        if not folder or not os.path.isdir(folder):
            return None
        files = sorted(glob.glob(os.path.join(folder, "*")))
        return next((f for f in files if re.search(pattern, os.path.basename(f), re.I)), None)

    @classmethod
    def _find_banner_file(cls, folder: Optional[str]) -> Optional[str]:
        return cls._find_file(folder, r"banner.*\.txt$|banner")

    @staticmethod
    def _read_text(path: Optional[str]) -> str:
        if not path or not os.path.exists(path):
            return ""
        with open(path, "r", errors="ignore") as f:
            return f.read()

    def _ingest_to_cas(self, path: str) -> Tuple[str, int]:
        return self.db._ingest_file_to_cas(path)

    def _ingest_possibly_gzip(self, src: str, event_folder: str) -> Tuple[str, str, int]:
        if src.endswith(".gz"):
            sha, size = self._ingest_to_cas(src)
            return sha, os.path.basename(src), size
        gz_name = os.path.basename(src) + ".gz"
        gz_tmp = os.path.join(event_folder, gz_name)
        with open(src, "rb") as fin, gzip.open(gz_tmp, "wb", compresslevel=5) as fout:
            shutil.copyfileobj(fin, fout)
        sha, size = self._ingest_to_cas(gz_tmp)
        os.remove(gz_tmp)
        return sha, gz_name, size

    def _record_artifact(self, event_id: str, kind: ArtifactKind, sha: str, filename: str, size: int) -> None:
        with self.db._conn() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (id, event_id, kind, sha256, filename, size_bytes)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(event_id, kind) DO UPDATE SET
                    sha256=excluded.sha256,
                    filename=excluded.filename,
                    size_bytes=excluded.size_bytes
                """,
                (str(uuid.uuid4()), event_id, kind, sha, filename, size),
            )

    @staticmethod
    def _parse_cross_section(banner_text: str) -> Optional[float]:
        patterns = [
            r"#\s*Integrated weight \(pb\)\s*:\s*([\d\.eE\-\+]+)",
            r"Integrated weight \(pb\)\s*[:=]\s*([\d\.eE\-\+]+)",
        ]
        for pat in patterns:
            m = re.search(pat, banner_text)
            if m:
                return float(m.group(1))
        return None

    @staticmethod
    def _parse_masses(banner_text: str) -> Dict[int, float]:
        masses: Dict[int, float] = {}
        m = re.search(r"BLOCK\s+MASS(.*?)(?:BLOCK|DECAY|</slha>|$)", banner_text, re.S | re.I)
        if not m:
            return masses
        for line in m.group(1).splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0].lstrip("-+").isdigit():
                try:
                    masses[int(parts[0])] = float(parts[1])
                except ValueError:
                    pass
        return masses

    @staticmethod
    def _parse_decay_info(banner_text: str) -> Dict[int, float]:
        info: Dict[int, float] = {}
        for pdg, width in re.findall(r"DECAY\s+([\-\+]?\d+)\s+([\d\.eE\-\+]+)", banner_text):
            try:
                info[int(pdg)] = float(width)
            except ValueError:
                continue
        return info

    @staticmethod
    def _parse_model(banner_text: str) -> Optional[str]:
        for name in re.findall(r"import\s+model\s+(\S+)", banner_text, re.I):
            if name.lower() != "sm":
                return name
        return None

    @staticmethod
    def _parse_seed(banner_text: str) -> Optional[int]:
        patterns = [
            r"iseed\s*=\s*(\d+)",
            r"(\d+)\s*=\s*iseed",
        ]
        for pat in patterns:
            m = re.search(pat, banner_text, re.I)
            if m:
                return int(m.group(1))
        return None

    @staticmethod
    def _generate_seed() -> int:
        return int.from_bytes(os.urandom(4), "big") % 2_147_483_646 + 1

    @classmethod
    def _collect_madgraph_metadata(
        cls,
        *,
        run_folder: str,
        pre_decay_folder: Optional[str],
        scan_row: Dict[str, Any],
        seed: Optional[int],
        seed_source: str,
        model: Optional[str],
        source_hepmc_filename: str,
    ) -> Dict[str, Any]:
        decayed_banner = cls._read_text(cls._find_banner_file(run_folder))
        pre_banner = cls._read_text(cls._find_banner_file(pre_decay_folder)) if pre_decay_folder else ""
        return {
            "model": model,
            "seed": seed,
            "seed_source": seed_source,
            "source_hepmc_filename": source_hepmc_filename,
            "decayed_run": {
                "run_name": os.path.basename(run_folder.rstrip(os.sep)),
                "cards": cls._collect_cards(run_folder, decayed_banner),
                "file_hashes": cls._hash_small_config_files(run_folder),
            },
            "pre_decay_run": {
                "run_name": os.path.basename(pre_decay_folder.rstrip(os.sep)) if pre_decay_folder else None,
                "cards": cls._collect_cards(pre_decay_folder, pre_banner) if pre_decay_folder else {},
                "file_hashes": cls._hash_small_config_files(pre_decay_folder) if pre_decay_folder else {},
            },
            "scan": scan_row,
            "regeneration_note": (
                "Use seed + stored cards/scan metadata to recreate the MadGraph run. "
                "If seed_source is generated_by_database_import_missing_in_banner, the original random seed was absent; "
                "the generated seed is stored for future deterministic regeneration but cannot prove bitwise equivalence to the original run."
            ),
        }

    @classmethod
    def _collect_cards(cls, folder: Optional[str], banner_text: str = "") -> Dict[str, str]:
        cards: Dict[str, str] = {}
        if banner_text:
            cards.update(cls._extract_banner_cards(banner_text))
        if folder and os.path.isdir(folder):
            patterns = {
                "run_card": ["*run_card*.dat", "*run_card*.txt"],
                "param_card": ["*param_card*.dat", "*param_card*.txt"],
                "pythia_card": ["*pythia*card*.dat", "*pythia*card*.txt"],
                "madspin_card": ["*madspin*card*.dat", "*madspin*card*.txt"],
                "proc_card": ["*proc_card*.dat", "*proc_card*.txt"],
                "banner": ["*banner*.txt"],
            }
            for key, globs in patterns.items():
                if key in cards:
                    continue
                for g in globs:
                    matches = sorted(glob.glob(os.path.join(folder, g)))
                    if matches:
                        cards[key] = cls._read_text(matches[0])
                        break
        return cards

    @staticmethod
    def _extract_banner_cards(banner_text: str) -> Dict[str, str]:
        tag_map = {
            "MGRunCard": "run_card",
            "slha": "param_card",
            "MGProcCard": "proc_card",
            "MGGenerationInfo": "generation_info",
            "MGPythia8Card": "pythia_card",
            "MadSpinCard": "madspin_card",
        }
        cards: Dict[str, str] = {}
        for tag, key in tag_map.items():
            m = re.search(rf"<{tag}>(.*?)</{tag}>", banner_text, re.S | re.I)
            if m:
                cards[key] = m.group(1).strip()
        return cards

    @staticmethod
    def _hash_small_config_files(folder: Optional[str], max_bytes: int = 20_000_000) -> Dict[str, str]:
        if not folder or not os.path.isdir(folder):
            return {}
        out: Dict[str, str] = {}
        keep = re.compile(r"(banner|card|param|run|pythia|madspin|proc|scan|tag)", re.I)
        for path in sorted(glob.glob(os.path.join(folder, "*"))):
            if not os.path.isfile(path):
                continue
            if os.path.getsize(path) > max_bytes:
                continue
            name = os.path.basename(path)
            if keep.search(name):
                out[name] = EventDatabaseManager._sha256_file(path)
        return out

    @classmethod
    def _compute_run_hash(cls, run_folder: str, pre_decay_folder: Optional[str], metadata: Dict[str, Any]) -> str:
        h = hashlib.sha256()
        for folder in [pre_decay_folder, run_folder]:
            if not folder:
                continue
            for path in sorted(glob.glob(os.path.join(folder, "*"))):
                if not os.path.isfile(path):
                    continue
                name = os.path.basename(path)
                # Include HEPMC in the identity hash, but not in CAS storage.
                if re.search(r"(banner|card|param|run|pythia|madspin|proc|scan|\.lhe|\.hepmc)", name, re.I):
                    h.update(name.encode())
                    with open(path, "rb") as f:
                        for chunk in iter(lambda: f.read(1024 * 1024), b""):
                            h.update(chunk)
        h.update(json.dumps(metadata.get("scan", {}), sort_keys=True, default=str).encode())
        return h.hexdigest()

    @staticmethod
    def _parse_scan_table(events_folder: str) -> Dict[str, Dict[str, Any]]:
        candidates = sorted(
            glob.glob(os.path.join(events_folder, "scan_run*.txt")) +
            glob.glob(os.path.join(events_folder, "scan_run_*.txt"))
        )
        if not candidates:
            return {}
        path = max(candidates, key=lambda p: os.path.getmtime(p))
        mapping: Dict[str, Dict[str, Any]] = {}
        header_cols: List[str] = []
        with open(path, "r", errors="ignore") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                if line.lstrip().startswith("#"):
                    hdr = line.lstrip()[1:].strip()
                    if hdr:
                        header_cols = re.split(r"\s+", hdr)
                    continue
                if not header_cols:
                    continue
                parts = re.split(r"\s+", line.strip())
                if not parts:
                    continue
                n = min(len(parts), len(header_cols))
                row = {header_cols[i]: parts[i] for i in range(n)}
                run = row.get("run_name") or row.get("run") or row.get("name")
                if not run:
                    continue
                cross_val: Optional[float] = None
                params: Dict[str, Any] = {}
                widths: Dict[str, Any] = {}
                raw: Dict[str, Any] = {}
                for k, v in row.items():
                    try:
                        num: Any = float(v)
                    except Exception:
                        num = v
                    raw[k] = num
                    if k in ("run_name", "run", "name"):
                        continue
                    if k.lower() == "cross":
                        cross_val = num if isinstance(num, float) else None
                    elif k.lower().startswith("width"):
                        widths[k] = num
                    else:
                        params[k] = num
                normalized = {"run_name": run, "cross": cross_val, "params": params, "widths": widths, "raw": raw}
                mapping[run] = normalized
                mapping[EventImporter._scan_base_key(run)] = normalized
        print(f"Parsed scan table from {os.path.basename(path)} with {len(mapping)} keys")
        return mapping


class EventAccessor:
    """Query, inspect, transform, and export records from an event database."""

    def __init__(self, db: EventDatabaseManager):
        self.db = db
        self._transforms: Dict[str, Transform] = {}

    def register_transform(self, name: str, func: Transform) -> None:
        self._transforms[name] = func

    def available_transforms(self) -> List[str]:
        return sorted(self._transforms.keys())

    def run_transform(self, event_id: str, name: str, output_dir: str) -> None:
        if name not in self._transforms:
            raise KeyError(f"Unknown transform: {name}")
        os.makedirs(output_dir, exist_ok=True)
        self._transforms[name](self, event_id, output_dir)

    def query(
        self,
        *,
        model: Optional[str] = None,
        is_decayed: Optional[bool] = None,
        run_name: Optional[str] = None,
        run_name_like: Optional[str] = None,
        llp_pid: Optional[int] = None,
        has_bundle: Optional[bool] = None,
        where: str = "",
        params: Tuple[Any, ...] = (),
    ) -> List[sqlite3.Row]:
        sql = (
            "SELECT e.*, m.name as model FROM events e "
            "LEFT JOIN models m ON e.model_id=m.id WHERE 1=1"
        )
        args: List[Any] = []
        if model:
            sql += " AND m.name=?"; args.append(model)
        if is_decayed is not None:
            sql += " AND e.is_decayed=?"; args.append(int(is_decayed))
        if run_name:
            sql += " AND e.run_name=?"; args.append(run_name)
        if run_name_like:
            sql += " AND e.run_name LIKE ?"; args.append(run_name_like)
        if llp_pid is not None:
            sql += " AND e.llp_pid=?"; args.append(int(llp_pid))
        if has_bundle is not None:
            sql += " AND e.sample_bundle_sha256 IS " + ("NOT NULL" if has_bundle else "NULL")
        if where:
            sql += f" AND ({where})"; args.extend(params)
        sql += " ORDER BY date_added DESC"
        with self.db._conn() as conn:
            return list(conn.execute(sql, tuple(args)))

    def get_event(self, event_id: str) -> Optional[Event]:
        with self.db._conn() as conn:
            row = conn.execute(
                "SELECT e.*, m.name as model FROM events e LEFT JOIN models m ON e.model_id=m.id WHERE e.id=?",
                (event_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_event(row)

    @staticmethod
    def _row_get(row: sqlite3.Row, key: str, default: Any = None) -> Any:
        return row[key] if key in row.keys() else default

    @classmethod
    def _row_to_event(cls, row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            model=cls._row_get(row, "model"),
            date_added=row["date_added"],
            is_decayed=bool(row["is_decayed"]) if row["is_decayed"] is not None else None,
            cross_section=row["cross_section"],
            path=row["path"],
            lhe_sha256=row["lhe_sha256"],
            hepmc_sha256=row["hepmc_sha256"],
            masses_json=row["masses_json"],
            seed=row["seed"],
            run_hash=row["run_hash"],
            decay_info_json=row["decay_info_json"],
            banner_text=row["banner_text"],
            run_name=cls._row_get(row, "run_name"),
            scan_params_json=cls._row_get(row, "scan_params_json"),
            scan_widths_json=cls._row_get(row, "scan_widths_json"),
            sample_bundle_sha256=cls._row_get(row, "sample_bundle_sha256"),
            sample_bundle_format=cls._row_get(row, "sample_bundle_format"),
            bundle_metadata_json=cls._row_get(row, "bundle_metadata_json"),
            unknown_pids_json=cls._row_get(row, "unknown_pids_json"),
            llp_pid=cls._row_get(row, "llp_pid"),
            pt_min_cfg_json=cls._row_get(row, "pt_min_cfg_json"),
            madgraph_metadata_json=cls._row_get(row, "madgraph_metadata_json"),
            pre_decay_run_name=cls._row_get(row, "pre_decay_run_name"),
            source_hepmc_filename=cls._row_get(row, "source_hepmc_filename"),
            source_hepmc_size_bytes=cls._row_get(row, "source_hepmc_size_bytes"),
            decayed_run_dir_size_bytes=cls._row_get(row, "decayed_run_dir_size_bytes"),
            pre_decay_run_dir_size_bytes=cls._row_get(row, "pre_decay_run_dir_size_bytes"),
            original_runs_total_size_bytes=cls._row_get(row, "original_runs_total_size_bytes"),
            stored_bundle_size_bytes=cls._row_get(row, "stored_bundle_size_bytes"),
            storage_metadata_json=cls._row_get(row, "storage_metadata_json"),
            sample_bundle_stage=cls._row_get(row, "sample_bundle_stage"),
            bundle_processing_json=cls._row_get(row, "bundle_processing_json"),
        )

    def get_artifacts(self, event_id: str) -> List[sqlite3.Row]:
        with self.db._conn() as conn:
            return list(conn.execute(
                "SELECT kind, sha256, filename, size_bytes FROM artifacts WHERE event_id=? ORDER BY kind",
                (event_id,),
            ))

    def artifact_path(self, sha256: str) -> str:
        return self.db._cas_path(sha256)

    def get_bundle_path(self, event_id: str) -> str:
        ev = self.get_event(event_id)
        if not ev:
            raise ValueError(f"Event {event_id} not found")
        if not ev.sample_bundle_sha256:
            raise ValueError(f"Event {event_id} has no stored dataframe bundle")
        return self.artifact_path(ev.sample_bundle_sha256)

    def get_sample_bundle(self, event_id: str) -> Dict[str, "pd.DataFrame"]:
        ev = self.get_event(event_id)
        if not ev:
            raise ValueError(f"Event {event_id} not found")
        path = self.get_bundle_path(event_id)
        return DataframeBundleIO.load_bundle(path, ev.sample_bundle_format)

    def export_sample_bundle(self, event_id: str, output_path: str) -> str:
        src = self.get_bundle_path(event_id)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        shutil.copy2(src, output_path)
        return output_path

    def get_bundle_metadata(self, event_id: str) -> Dict[str, Any]:
        ev = self.get_event(event_id)
        if not ev or not ev.bundle_metadata_json:
            return {}
        return json.loads(ev.bundle_metadata_json)

    def get_bundle_processing(self, event_id: str) -> Dict[str, Any]:
        ev = self.get_event(event_id)
        if not ev:
            return {}
        if ev.bundle_processing_json:
            return json.loads(ev.bundle_processing_json)
        meta = self.get_bundle_metadata(event_id)
        return meta.get("processing", {}) if isinstance(meta, dict) else {}

    def get_selection_ready_bundle(self, event_id: str, *, require_ready: bool = True) -> Dict[str, "pd.DataFrame"]:
        ev = self.get_event(event_id)
        if not ev:
            raise ValueError(f"Event {event_id} not found")
        bundle = self.get_sample_bundle(event_id)
        missing = [k for k in SELECTION_ENGINE_BUNDLE_KEYS if k not in bundle]
        if require_ready and (ev.sample_bundle_stage != SAMPLE_BUNDLE_STAGE_SELECTION_READY or missing):
            raise ValueError(
                f"Event {event_id} is not a selection-ready bundle "
                f"(stage={ev.sample_bundle_stage}, missing={missing})"
            )
        return bundle

    def repack_bundle_selection_ready(
        self,
        event_id: str,
        *,
        selection_min_pt: Optional[Dict[str, float]] = None,
        selection_min_p: Optional[Dict[str, float]] = None,
        prune_bundle: bool = True,
        bundle_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert an existing full LLPAnalyzer bundle into a compact selection-ready bundle.

        This can add jets/isolation/pruning to old bundles. It cannot apply phi-folding,
        because phi-folding must happen on the raw HepMC DataFrame before LLPAnalyzer.
        Reimport from HEPMC for that case.
        """
        ev = self.get_event(event_id)
        if not ev:
            raise ValueError(f"Event {event_id} not found")
        bundle = self.get_sample_bundle(event_id)
        bundle2, processing = EventImporter._prepare_selection_ready_bundle(
            bundle,
            llp_pid=int(ev.llp_pid or 0),
            selection_min_pt=selection_min_pt,
            selection_min_p=selection_min_p,
            build_jets=True,
            compute_isolation=True,
            prune_bundle=prune_bundle,
        )
        processing["repacked_from_existing_bundle"] = True
        processing["phi_fold"] = False
        processing["warning"] = "Phi-fold cannot be added during repack; reimport from HEPMC if needed."

        out_dir = ev.path or os.path.join(self.db._events_root, event_id)
        os.makedirs(out_dir, exist_ok=True)
        fmt = bundle_format or ev.sample_bundle_format or DataframeBundleIO.PICKLE_GZIP
        basename = f"{ev.run_name or event_id}_selection_ready"
        bundle_path, fmt, metadata = DataframeBundleIO.save_bundle(
            bundle2, out_dir, basename, requested_format=fmt, metadata_extra={"processing": processing}
        )
        sha, size = self.db._ingest_file_to_cas(bundle_path)
        self.db._link_into_event_folder(sha, out_dir, os.path.basename(bundle_path))
        EventImporter(self.db)._record_artifact(event_id, ARTIFACT_SAMPLE_BUNDLE, sha, os.path.basename(bundle_path), int(size))

        storage_meta = self.get_storage_metadata(event_id)
        if storage_meta:
            storage_meta.setdefault("stored", {})["bundle_filename"] = os.path.basename(bundle_path)
            storage_meta.setdefault("stored", {})["bundle_size_bytes"] = int(size)
            storage_meta.setdefault("stored", {})["bundle_size_human"] = EventImporter._format_bytes(int(size))
            src = storage_meta.get("source", {}).get("hepmc_size_bytes")
            orig = storage_meta.get("source", {}).get("original_runs_total_size_bytes")
            storage_meta["comparison"] = {
                "bundle_over_source_hepmc": EventImporter._safe_ratio(int(size), src),
                "bundle_over_original_runs": EventImporter._safe_ratio(int(size), orig),
                "saved_vs_source_hepmc_bytes": (int(src) - int(size)) if src is not None else None,
                "saved_vs_original_runs_bytes": (int(orig) - int(size)) if orig else None,
                "saved_vs_original_runs_fraction": (1.0 - (int(size) / int(orig))) if orig else None,
            }

        with self.db._conn() as conn:
            conn.execute(
                """
                UPDATE events SET sample_bundle_sha256=?, sample_bundle_format=?, bundle_metadata_json=?,
                    stored_bundle_size_bytes=?, sample_bundle_stage=?, bundle_processing_json=?, storage_metadata_json=?
                WHERE id=?
                """,
                (
                    sha, fmt, json.dumps(metadata), int(size), SAMPLE_BUNDLE_STAGE_SELECTION_READY,
                    json.dumps(processing), json.dumps(storage_meta) if storage_meta else ev.storage_metadata_json, event_id,
                ),
            )
        return {"event_id": event_id, "ok": True, "sha256": sha, "size_bytes": int(size), "processing": processing}

    def get_madgraph_metadata(self, event_id: str) -> Dict[str, Any]:
        ev = self.get_event(event_id)
        if not ev or not ev.madgraph_metadata_json:
            return {}
        return json.loads(ev.madgraph_metadata_json)

    def storage_stats(self) -> Dict[str, Any]:
        with self.db._conn() as conn:
            blobs = conn.execute("SELECT COUNT(*), SUM(size_bytes) FROM cas_blobs").fetchone()
            events = conn.execute("SELECT COUNT(*) FROM events").fetchone()
            models = conn.execute("SELECT COUNT(*) FROM models").fetchone()
            bundles = conn.execute("SELECT COUNT(*) FROM events WHERE sample_bundle_sha256 IS NOT NULL").fetchone()
            hepmc = conn.execute("SELECT COUNT(*) FROM events WHERE hepmc_sha256 IS NOT NULL").fetchone()
        return {
            "events": int(events[0] or 0),
            "models": int(models[0] or 0),
            "events_with_bundles": int(bundles[0] or 0),
            "events_with_stored_hepmc": int(hepmc[0] or 0),
            "cas_blobs": int(blobs[0] or 0),
            "cas_size_bytes": int(blobs[1] or 0),
        }

    def regenerate_runs(
        self,
        madgraph_factory: MadGraphFactory,
        *,
        event_ids: Optional[Iterable[str]] = None,
        model: Optional[str] = None,
        where: str = "",
        params: Tuple[Any, ...] = (),
        output_root: str = "db/Temp/regenerated_madgraph",
        retrieve_width_mode: bool = False,
    ) -> List[RegenerationResult]:
        """Regenerate one or many MadGraph runs selected by ids or filters.

        `madgraph_factory` receives the stored Event and metadata and must return an
        object compatible with MadgraphInterface: `.run()` and `.retrieve_events(path, width_mode=...)`.

        Supported factory signatures:
          factory(event=event, metadata=metadata)
          factory(event, metadata)
          factory(metadata)
        """
        if event_ids is None:
            rows = self.query(model=model, where=where, params=params)
            ids = [r["id"] for r in rows]
        else:
            ids = list(event_ids)
        os.makedirs(output_root, exist_ok=True)
        results: List[RegenerationResult] = []
        for event_id in ids:
            ev = self.get_event(event_id)
            if not ev:
                results.append(RegenerationResult(event_id, None, output_root, False, "event not found"))
                continue
            metadata = self.get_madgraph_metadata(event_id)
            out_path = os.path.join(output_root, ev.run_name or event_id)
            try:
                interface = self._call_madgraph_factory(madgraph_factory, ev, metadata)
                if not hasattr(interface, "run") or not hasattr(interface, "retrieve_events"):
                    raise TypeError("madgraph_factory must return an object with run() and retrieve_events()")
                interface.run()
                try:
                    interface.retrieve_events(out_path, width_mode=retrieve_width_mode)
                except TypeError:
                    interface.retrieve_events(out_path)
                results.append(RegenerationResult(event_id, ev.run_name, out_path, True))
            except Exception as exc:
                results.append(RegenerationResult(event_id, ev.run_name, out_path, False, repr(exc)))
        return results

    @staticmethod
    def _call_madgraph_factory(factory: MadGraphFactory, ev: Event, metadata: Dict[str, Any]) -> Any:
        try:
            sig = inspect.signature(factory)
            params = sig.parameters
            if "event" in params or "metadata" in params:
                kwargs = {}
                if "event" in params:
                    kwargs["event"] = ev
                if "metadata" in params:
                    kwargs["metadata"] = metadata
                return factory(**kwargs)
        except (TypeError, ValueError):
            pass
        try:
            return factory(ev, metadata)
        except TypeError:
            return factory(metadata)


    @staticmethod
    def _loads_json(value: Optional[str], default: Any = None) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except Exception:
            return default

    def get_storage_metadata(self, event_id: str) -> Dict[str, Any]:
        ev = self.get_event(event_id)
        if not ev or not ev.storage_metadata_json:
            return {}
        return json.loads(ev.storage_metadata_json)

    def _artifact_summary(self) -> List[Dict[str, Any]]:
        with self.db._conn() as conn:
            rows = conn.execute("""
                SELECT kind, COUNT(*) AS n, COALESCE(SUM(size_bytes), 0) AS size_bytes
                FROM artifacts GROUP BY kind ORDER BY size_bytes DESC
            """).fetchall()
        return [{"kind": r["kind"], "count": int(r["n"] or 0), "size_bytes": int(r["size_bytes"] or 0)} for r in rows]

    def list_models(self) -> List[Dict[str, Any]]:
        with self.db._conn() as conn:
            rows = conn.execute("""
                SELECT m.name AS model, COUNT(e.id) AS n_events,
                       SUM(CASE WHEN e.sample_bundle_sha256 IS NOT NULL THEN 1 ELSE 0 END) AS n_bundles,
                       SUM(CASE WHEN e.hepmc_sha256 IS NOT NULL THEN 1 ELSE 0 END) AS n_stored_hepmc,
                       COALESCE(SUM(e.source_hepmc_size_bytes), 0) AS source_hepmc_size_bytes,
                       COALESCE(SUM(e.original_runs_total_size_bytes), 0) AS original_runs_total_size_bytes,
                       COALESCE(SUM(e.stored_bundle_size_bytes), 0) AS stored_bundle_size_bytes,
                       MIN(e.date_added) AS first_import, MAX(e.date_added) AS last_import
                FROM events e LEFT JOIN models m ON e.model_id=m.id
                GROUP BY m.name ORDER BY n_events DESC, model
            """).fetchall()
        return [dict(r) for r in rows]

    def events_table(self, *, model: Optional[str] = None, llp_pid: Optional[int] = None, has_bundle: Optional[bool] = None,
                     limit: Optional[int] = None, include_json: bool = False) -> List[Dict[str, Any]]:
        rows = self.query(model=model, llp_pid=llp_pid, has_bundle=has_bundle)
        if limit is not None:
            rows = rows[: int(limit)]
        out: List[Dict[str, Any]] = []
        for r in rows:
            item = {
                "id": r["id"], "date_added": r["date_added"], "model": r["model"],
                "run_name": self._row_get(r, "run_name"), "pre_decay_run_name": self._row_get(r, "pre_decay_run_name"),
                "cross_section_pb": r["cross_section"], "seed": r["seed"], "llp_pid": self._row_get(r, "llp_pid"),
                "sample_bundle_format": self._row_get(r, "sample_bundle_format"),
                "sample_bundle_stage": self._row_get(r, "sample_bundle_stage"),
                "source_hepmc_filename": self._row_get(r, "source_hepmc_filename"),
                "source_hepmc_size_bytes": self._row_get(r, "source_hepmc_size_bytes"),
                "decayed_run_dir_size_bytes": self._row_get(r, "decayed_run_dir_size_bytes"),
                "pre_decay_run_dir_size_bytes": self._row_get(r, "pre_decay_run_dir_size_bytes"),
                "original_runs_total_size_bytes": self._row_get(r, "original_runs_total_size_bytes"),
                "stored_bundle_size_bytes": self._row_get(r, "stored_bundle_size_bytes"),
                "hepmc_stored": bool(r["hepmc_sha256"]),
            }
            src = item.get("source_hepmc_size_bytes") or 0; orig = item.get("original_runs_total_size_bytes") or 0; bundle = item.get("stored_bundle_size_bytes") or 0
            item["bundle_over_hepmc"] = (bundle / src) if src else None
            item["bundle_over_original_runs"] = (bundle / orig) if orig else None
            item["saved_vs_original_runs_bytes"] = (orig - bundle) if orig else None
            if include_json:
                item["scan_params"] = self._loads_json(self._row_get(r, "scan_params_json"), {})
                item["scan_widths"] = self._loads_json(self._row_get(r, "scan_widths_json"), {})
                item["bundle_metadata"] = self._loads_json(self._row_get(r, "bundle_metadata_json"), {})
                item["bundle_processing"] = self._loads_json(self._row_get(r, "bundle_processing_json"), {})
                item["storage_metadata"] = self._loads_json(self._row_get(r, "storage_metadata_json"), {})
                item["madgraph_metadata"] = self._loads_json(self._row_get(r, "madgraph_metadata_json"), {})
            out.append(item)
        return out

    def bundle_frame_summary(self) -> Dict[str, Dict[str, Any]]:
        summary: Dict[str, Dict[str, Any]] = {}
        for r in self.query(has_bundle=True):
            meta = self._loads_json(self._row_get(r, "bundle_metadata_json"), {}) or {}
            for frame, info in (meta.get("frames") or {}).items():
                slot = summary.setdefault(frame, {"events": 0, "rows": 0, "memory_bytes": 0})
                slot["events"] += 1; slot["rows"] += int(info.get("rows") or 0); slot["memory_bytes"] += int(info.get("memory_bytes") or 0)
        return summary

    def bundle_stage_summary(self) -> Dict[str, int]:
        with self.db._conn() as conn:
            rows = conn.execute(
                """
                SELECT COALESCE(sample_bundle_stage, 'legacy_or_unknown') AS stage, COUNT(*) AS n
                FROM events WHERE sample_bundle_sha256 IS NOT NULL
                GROUP BY COALESCE(sample_bundle_stage, 'legacy_or_unknown')
                ORDER BY n DESC
                """
            ).fetchall()
        return {str(r["stage"]): int(r["n"] or 0) for r in rows}

    def storage_stats(self) -> Dict[str, Any]:
        with self.db._conn() as conn:
            blobs = conn.execute("SELECT COUNT(*), COALESCE(SUM(size_bytes), 0) FROM cas_blobs").fetchone()
            totals = conn.execute("""
                SELECT COUNT(*) AS events, COUNT(DISTINCT model_id) AS models,
                       SUM(CASE WHEN sample_bundle_sha256 IS NOT NULL THEN 1 ELSE 0 END) AS events_with_bundles,
                       SUM(CASE WHEN hepmc_sha256 IS NOT NULL THEN 1 ELSE 0 END) AS events_with_stored_hepmc,
                       COALESCE(SUM(source_hepmc_size_bytes), 0) AS source_hepmc_size_bytes,
                       COALESCE(SUM(original_runs_total_size_bytes), 0) AS original_runs_total_size_bytes,
                       COALESCE(SUM(stored_bundle_size_bytes), 0) AS stored_bundle_size_bytes
                FROM events
            """).fetchone()
        source_hepmc = int(totals["source_hepmc_size_bytes"] or 0); original_runs = int(totals["original_runs_total_size_bytes"] or 0); bundles = int(totals["stored_bundle_size_bytes"] or 0)
        return {
            "events": int(totals["events"] or 0), "models": int(totals["models"] or 0),
            "events_with_bundles": int(totals["events_with_bundles"] or 0),
            "events_with_stored_hepmc": int(totals["events_with_stored_hepmc"] or 0),
            "cas_blobs": int(blobs[0] or 0), "cas_size_bytes": int(blobs[1] or 0),
            "source_hepmc_size_bytes": source_hepmc, "original_runs_total_size_bytes": original_runs, "stored_bundle_size_bytes": bundles,
            "saved_vs_source_hepmc_bytes": source_hepmc - bundles if source_hepmc else None,
            "saved_vs_original_runs_bytes": original_runs - bundles if original_runs else None,
            "bundle_over_source_hepmc": (bundles / source_hepmc) if source_hepmc else None,
            "bundle_over_original_runs": (bundles / original_runs) if original_runs else None,
            "artifacts_by_kind": self._artifact_summary(),
            "bundle_frames": self.bundle_frame_summary(),
            "bundle_stages": self.bundle_stage_summary(),
        }

    def dashboard_payload(self, *, event_limit: Optional[int] = None, include_particles: bool = False) -> Dict[str, Any]:
        payload = {"created_at": dt.datetime.now().isoformat(), "storage": self.storage_stats(), "models": self.list_models(), "events": self.events_table(limit=event_limit)}
        if include_particles:
            payload["particles"] = self.list_particles(include_decays=False)
        return payload

    def _stored_bundle_size(self, event_id: str, ev: Optional[Event] = None) -> int:
        ev = ev or self.get_event(event_id)
        if ev and ev.stored_bundle_size_bytes:
            return int(ev.stored_bundle_size_bytes)
        for art in self.get_artifacts(event_id):
            if art["kind"] == ARTIFACT_SAMPLE_BUNDLE:
                return int(art["size_bytes"] or 0)
        if ev and ev.sample_bundle_sha256:
            path = self.artifact_path(ev.sample_bundle_sha256)
            if os.path.exists(path): return int(os.path.getsize(path))
        return 0

    def refresh_storage_metadata_from_events_root(self, events_root: str, *, event_ids: Optional[Iterable[str]] = None, dry_run: bool = False) -> List[Dict[str, Any]]:
        if not os.path.isdir(events_root): raise FileNotFoundError(events_root)
        run_folders = {os.path.basename(p.rstrip(os.sep)): p for p in glob.glob(os.path.join(events_root, "*")) if os.path.isdir(p)}
        ids = list(event_ids) if event_ids is not None else [r["id"] for r in self.query()]
        results: List[Dict[str, Any]] = []
        for event_id in ids:
            ev = self.get_event(event_id)
            if not ev:
                results.append({"event_id": event_id, "ok": False, "error": "event not found"}); continue
            run_folder = run_folders.get(ev.run_name or "")
            pre_decay_folder = run_folders.get(ev.pre_decay_run_name or "")
            if not pre_decay_folder and ev.run_name:
                pre_decay_folder = run_folders.get(EventImporter._scan_base_key(ev.run_name))
            if not run_folder:
                results.append({"event_id": event_id, "run_name": ev.run_name, "ok": False, "error": "run folder not found"}); continue
            hepmc_file = EventImporter._find_file(run_folder, r"\.hepmc(\.gz)?$")
            bundle_size = self._stored_bundle_size(event_id, ev)
            source_hepmc_size = os.path.getsize(hepmc_file) if hepmc_file and os.path.exists(hepmc_file) else None
            decayed_size = EventImporter._dir_size(run_folder); pre_size = EventImporter._dir_size(pre_decay_folder) if pre_decay_folder else None
            original_total = EventImporter._sum_unique_directory_sizes([pre_decay_folder, run_folder])
            metadata = EventImporter._build_storage_metadata(run_folder=run_folder, pre_decay_folder=pre_decay_folder, hepmc_file=hepmc_file, bundle_path=self.get_bundle_path(event_id) if ev.sample_bundle_sha256 else None, source_hepmc_size_bytes=source_hepmc_size, decayed_run_dir_size_bytes=decayed_size, pre_decay_run_dir_size_bytes=pre_size, original_runs_total_size_bytes=original_total, stored_bundle_size_bytes=bundle_size)
            if not dry_run:
                with self.db._conn() as conn:
                    conn.execute("""
                        UPDATE events SET source_hepmc_size_bytes=?, decayed_run_dir_size_bytes=?, pre_decay_run_dir_size_bytes=?, original_runs_total_size_bytes=?, stored_bundle_size_bytes=?, storage_metadata_json=? WHERE id=?
                    """, (int(source_hepmc_size) if source_hepmc_size is not None else None, int(decayed_size), int(pre_size) if pre_size is not None else None, int(original_total), int(bundle_size or 0), json.dumps(metadata), event_id))
            results.append({"event_id": event_id, "run_name": ev.run_name, "ok": True, "storage_metadata": metadata})
        return results

    def list_particles(self, *, model: Optional[str] = None, event_id: Optional[str] = None, include_decays: bool = False) -> List[Dict[str, Any]]:
        rows = [self.get_event(event_id)] if event_id else [self._row_to_event(r) for r in self.query(model=model)]
        merged: Dict[Tuple[Optional[str], int], Dict[str, Any]] = {}
        for ev in rows:
            if not ev or not ev.banner_text: continue
            catalog = BannerInfoParser.particle_catalog(ev.banner_text, include_decays=include_decays)
            for pinfo in catalog["particles"]:
                key = (ev.model, int(pinfo["pdg"]))
                slot = merged.setdefault(key, {**pinfo, "model": ev.model, "event_ids": [], "run_names": [], "occurrences": 0})
                slot.update({k: v for k, v in pinfo.items() if v is not None})
                slot["event_ids"].append(ev.id); slot["run_names"].append(ev.run_name); slot["occurrences"] += 1
        return sorted(merged.values(), key=lambda x: (str(x.get("model")), int(x.get("pdg", 0))))

    def get_particle_info(self, pdg: int, *, model: Optional[str] = None, event_id: Optional[str] = None, max_channels: int = 50) -> Optional[Dict[str, Any]]:
        pdg = int(pdg); rows = [self.get_event(event_id)] if event_id else [self._row_to_event(r) for r in self.query(model=model)]
        occurrences: List[Dict[str, Any]] = []; best: Optional[Dict[str, Any]] = None
        for ev in rows:
            if not ev or not ev.banner_text: continue
            catalog = BannerInfoParser.particle_catalog(ev.banner_text, include_decays=True, max_channels=max_channels)
            match = next((p for p in catalog["particles"] if int(p.get("pdg")) == pdg), None)
            if not match: continue
            if best is None: best = {**match, "model": ev.model, "generation_info": catalog.get("generation_info")}
            occurrences.append({"event_id": ev.id, "run_name": ev.run_name, "model": ev.model})
        if best is None: return None
        best["occurrences"] = occurrences
        return best



def register_example_transforms(accessor: EventAccessor) -> None:
    accessor.register_transform("to_json", _transform_to_json)
    accessor.register_transform("report_txt", _transform_report_txt)
    accessor.register_transform("export_bundle", _transform_export_bundle)


def _decode_json_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    for field in (
        "masses_json", "decay_info_json", "scan_params_json", "scan_widths_json",
        "bundle_metadata_json", "unknown_pids_json", "pt_min_cfg_json", "madgraph_metadata_json", "storage_metadata_json",
    ):
        if payload.get(field):
            try:
                payload[field.replace("_json", "")] = json.loads(payload[field])
            except Exception:
                payload[field.replace("_json", "")] = None
    return payload


def _transform_to_json(acc: EventAccessor, event_id: str, output_dir: str) -> None:
    ev = acc.get_event(event_id)
    if not ev:
        raise ValueError(f"Event {event_id} not found")
    artifacts = [dict(row) for row in acc.get_artifacts(event_id)]
    payload = _decode_json_fields(asdict(ev))
    out_path = os.path.join(output_dir, f"{event_id}.json")
    with open(out_path, "w") as f:
        json.dump({**payload, "artifacts": artifacts}, f, indent=2)
    print(f"Wrote {out_path}")


def _transform_report_txt(acc: EventAccessor, event_id: str, output_dir: str) -> None:
    ev = acc.get_event(event_id)
    if not ev:
        raise ValueError(f"Event {event_id} not found")
    meta = acc.get_bundle_metadata(event_id)
    mg = acc.get_madgraph_metadata(event_id)
    lines = [
        f"Event: {ev.id}",
        f"Run: {ev.run_name}",
        f"Pre-decay run: {ev.pre_decay_run_name}",
        f"Model: {ev.model}",
        f"Date: {ev.date_added}",
        f"Decayed: {ev.is_decayed}",
        f"Cross-section (pb): {ev.cross_section}",
        f"Seed: {ev.seed}",
        f"Seed source: {mg.get('seed_source')}",
        f"LLP PID: {ev.llp_pid}",
        f"Bundle SHA256: {ev.sample_bundle_sha256}",
        f"Bundle format: {ev.sample_bundle_format}",
        f"Bundle frames: {list((meta.get('frames') or {}).keys())}",
        f"HEPMC stored in DB: {bool(ev.hepmc_sha256)}",
    ]
    out_path = os.path.join(output_dir, f"{event_id}.txt")
    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {out_path}")


def _transform_export_bundle(acc: EventAccessor, event_id: str, output_dir: str) -> None:
    ev = acc.get_event(event_id)
    if not ev or not ev.sample_bundle_sha256:
        raise ValueError(f"Event {event_id} has no stored bundle")
    ext = ".parquet.zip" if ev.sample_bundle_format == DataframeBundleIO.PARQUET_ZIP else ".pkl.gz"
    out_path = os.path.join(output_dir, f"{event_id}_sampledfs{ext}")
    acc.export_sample_bundle(event_id, out_path)
    print(f"Wrote {out_path}")


# -----------------------------
# Programmatic helpers
# -----------------------------

def programmatic_import(
    events_root: str,
    model: Optional[str] = None,
    *,
    neo_manager: Any = None,
    llp_pid: Optional[int] = None,
    pt_min_cfg: Optional[Dict[str, float]] = None,
    bundle_format: str = DataframeBundleIO.PICKLE_GZIP,
    only_decayed: bool = True,
    store_lhe: bool = False,
    include_hepmc: bool = False,
    db_path: str = "db/EventsDatabase.db",
    storage_dir: str = "db/EventsStorage",
):
    db = EventDatabaseManager(db_path, storage_dir)
    importer = EventImporter(db)
    acc = EventAccessor(db)
    register_example_transforms(acc)
    imported = importer.import_from_events_folder(
        events_root,
        model=model,
        neo_manager=neo_manager,
        llp_pid=llp_pid,
        pt_min_cfg=pt_min_cfg,
        bundle_format=bundle_format,
        only_decayed=only_decayed,
        store_lhe=store_lhe,
        include_hepmc=include_hepmc,
    )
    return db, importer, acc, imported


def programmatic_list(acc: EventAccessor, **filters):
    return acc.query(**filters)


def programmatic_show(acc: EventAccessor, event_id: str) -> dict:
    ev = acc.get_event(event_id)
    arts = acc.get_artifacts(event_id)
    payload = _decode_json_fields(asdict(ev)) if ev else None
    return {"event": payload, "artifacts": [dict(a) for a in arts]}


def programmatic_get_bundle(acc: EventAccessor, event_id: str) -> Dict[str, "pd.DataFrame"]:
    return acc.get_sample_bundle(event_id)


def programmatic_dashboard_payload(acc: EventAccessor, *, event_limit: Optional[int] = None, include_particles: bool = False) -> Dict[str, Any]:
    return acc.dashboard_payload(event_limit=event_limit, include_particles=include_particles)


def programmatic_refresh_storage_metadata(acc: EventAccessor, events_root: str, *, dry_run: bool = False) -> List[Dict[str, Any]]:
    return acc.refresh_storage_metadata_from_events_root(events_root, dry_run=dry_run)


def programmatic_particle_info(acc: EventAccessor, pdg: int, *, model: Optional[str] = None, event_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    return acc.get_particle_info(pdg, model=model, event_id=event_id)


def programmatic_regenerate(
    acc: EventAccessor,
    madgraph_factory: MadGraphFactory,
    *,
    event_ids: Optional[Iterable[str]] = None,
    model: Optional[str] = None,
    where: str = "",
    params: Tuple[Any, ...] = (),
    output_root: str = "db/Temp/regenerated_madgraph",
) -> List[RegenerationResult]:
    return acc.regenerate_runs(
        madgraph_factory,
        event_ids=event_ids,
        model=model,
        where=where,
        params=params,
        output_root=output_root,
    )


# -----------------------------
# CLI
# -----------------------------

TEST_HELP = """
Examples:
  # Import decayed HEPMC into dataframe bundles, without storing HEPMC
  python EventDatabaseManager_storage_dashboard.py import \
    --events-root db/Temp/madgraph/Events/Events \
    --model SM_HeavyN_CKM_AllMasses_LO \
    --ufo-path Assets/UFO/UFO_HNL \
    --llp-pid 9900012 \
    --charged-pt-min 0.5

  python EventDatabaseManager_storage_dashboard.py list --model SM_HeavyN_CKM_AllMasses_LO --has-bundle
  python EventDatabaseManager_storage_dashboard.py show --id <EVENT_UUID>
  python EventDatabaseManager_storage_dashboard.py export-bundle --id <EVENT_UUID> --out out
  python EventDatabaseManager_storage_dashboard.py stats
"""


def _build_argparser():
    import argparse
    p = argparse.ArgumentParser(
        description="Events DB manager: stores LLPAnalyzer dataframe bundles instead of HEPMC",
        epilog=TEST_HELP,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("command", choices=["import", "list", "show", "transform", "export-bundle", "repack-selection-ready", "stats", "storage-refresh", "dashboard-json", "particles"])
    p.add_argument("--db", dest="db_path", default="db/EventsDatabase.db")
    p.add_argument("--storage", dest="storage_dir", default="db/EventsStorage")
    p.add_argument("--hardlinks", action="store_true")
    p.add_argument("--events-root", dest="events_root")
    p.add_argument("--model", dest="model")
    p.add_argument("--id", dest="event_id")
    p.add_argument("--name", dest="transform_name")
    p.add_argument("--out", dest="output_dir", default="out")
    p.add_argument("--ufo-path", dest="ufo_path")
    p.add_argument("--llp-pid", dest="llp_pid", type=int)
    p.add_argument("--charged-pt-min", dest="charged_pt_min", type=float, default=0.0)
    p.add_argument("--bundle-format", choices=[DataframeBundleIO.PICKLE_GZIP, DataframeBundleIO.PARQUET_ZIP, DataframeBundleIO.AUTO], default=DataframeBundleIO.PICKLE_GZIP)
    p.add_argument("--phi-fold", action="store_true", help="Apply PhiFoldTransform before LLPAnalyzer at import time")
    p.add_argument("--raw-bundle", action="store_true", help="Store the full LLPAnalyzer bundle without jets/isolation/pruning")
    p.add_argument("--keep-extra-frames", action="store_true", help="With selection-ready storage, keep intermediate frames too")
    p.add_argument("--iso-min-pt-llp", type=float, default=0.0)
    p.add_argument("--iso-min-pt-charged", type=float, default=5.0)
    p.add_argument("--iso-min-pt-neutral", type=float, default=5.0)
    p.add_argument("--iso-min-pt-jet", type=float, default=15.0)
    p.add_argument("--iso-min-p-llp", type=float, default=0.1)
    p.add_argument("--iso-min-p-charged", type=float, default=0.1)
    p.add_argument("--iso-min-p-neutral", type=float, default=0.1)
    p.add_argument("--iso-min-p-jet", type=float, default=0.1)
    p.add_argument("--all-runs", action="store_true", help="Import all run folders, not only decayed-looking runs")
    p.add_argument("--store-lhe", action="store_true", help="Also store LHE artifacts in CAS")
    p.add_argument("--include-hepmc", action="store_true", help="Legacy opt-in: also store HEPMC in CAS")
    p.add_argument("--has-bundle", action="store_true", help="List only events that have a stored dataframe bundle")
    p.add_argument("--limit", type=int, default=None, help="Limit rows exported by dashboard-json")
    p.add_argument("--pdg", type=int, default=None, help="PDG id for particles command")
    p.add_argument("--include-particles", action="store_true", help="Include parsed particle catalog in dashboard-json")
    p.add_argument("--include-decays", action="store_true", help="Include decay channels in particles output")
    p.add_argument("--dry-run", action="store_true", help="Compute storage metadata without writing DB changes")
    return p


def _make_neo_from_ufo_path(ufo_path: Optional[str]) -> Any:
    if not ufo_path:
        return None
    try:
        from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
    except Exception as exc:
        raise RuntimeError("Cannot import SetAnubisInterface; pass neo_manager programmatically instead") from exc
    return SetAnubisInterface(ufo_path)


def _cmd_import(args) -> None:
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    importer = EventImporter(db)
    neo = _make_neo_from_ufo_path(args.ufo_path)
    if args.llp_pid is not None and neo is None:
        raise SystemExit("--ufo-path is required when --llp-pid is provided from the CLI")
    pt_min_cfg = {"chargedTrack": float(args.charged_pt_min)}
    selection_min_pt = {
        "LLP": args.iso_min_pt_llp,
        "chargedTrack": args.iso_min_pt_charged,
        "neutralTrack": args.iso_min_pt_neutral,
        "jet": args.iso_min_pt_jet,
    }
    selection_min_p = {
        "LLP": args.iso_min_p_llp,
        "chargedTrack": args.iso_min_p_charged,
        "neutralTrack": args.iso_min_p_neutral,
        "jet": args.iso_min_p_jet,
    }
    imported = importer.import_from_events_folder(
        args.events_root,
        model=args.model,
        neo_manager=neo,
        llp_pid=args.llp_pid,
        pt_min_cfg=pt_min_cfg,
        bundle_format=args.bundle_format,
        selection_ready=not args.raw_bundle,
        phi_fold=args.phi_fold,
        prune_bundle=not args.keep_extra_frames,
        selection_min_pt=selection_min_pt,
        selection_min_p=selection_min_p,
        only_decayed=not args.all_runs,
        store_lhe=args.store_lhe,
        include_hepmc=args.include_hepmc,
    )
    print(f"Imported {len(imported)} events")


def _cmd_list(args) -> None:
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    rows = acc.query(model=args.model, has_bundle=True if args.has_bundle else None)
    for r in rows:
        print(
            f"{r['id']} | run={r['run_name']} | pre={r['pre_decay_run_name']} | model={r['model']} | "
            f"xsec={r['cross_section']} pb | llp={r['llp_pid']} | bundle={r['sample_bundle_format']} | stage={r['sample_bundle_stage']} | "
            f"bundle_size={r['stored_bundle_size_bytes']} B | hepmc_source={r['source_hepmc_size_bytes']} B | "
            f"hepmc_stored={bool(r['hepmc_sha256'])} | date={r['date_added']}"
        )
    print(f"Total: {len(rows)} events")


def _cmd_show(args) -> None:
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    payload = programmatic_show(acc, args.event_id)
    if not payload["event"]:
        print("Event not found")
        return
    print(json.dumps(payload, indent=2))


def _cmd_transform(args) -> None:
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    register_example_transforms(acc)
    if args.transform_name is None:
        print("Available:", ", ".join(acc.available_transforms()))
        return
    acc.run_transform(args.event_id, args.transform_name, args.output_dir)


def _cmd_export_bundle(args) -> None:
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    ev = acc.get_event(args.event_id)
    if not ev:
        raise SystemExit("Event not found")
    ext = ".parquet.zip" if ev.sample_bundle_format == DataframeBundleIO.PARQUET_ZIP else ".pkl.gz"
    out = args.output_dir
    if os.path.isdir(out) or not os.path.splitext(out)[1]:
        os.makedirs(out, exist_ok=True)
        out = os.path.join(out, f"{args.event_id}_sampledfs{ext}")
    acc.export_sample_bundle(args.event_id, out)
    print(f"Wrote {out}")


def _cmd_repack_selection_ready(args) -> None:
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    selection_min_pt = {
        "LLP": args.iso_min_pt_llp,
        "chargedTrack": args.iso_min_pt_charged,
        "neutralTrack": args.iso_min_pt_neutral,
        "jet": args.iso_min_pt_jet,
    }
    selection_min_p = {
        "LLP": args.iso_min_p_llp,
        "chargedTrack": args.iso_min_p_charged,
        "neutralTrack": args.iso_min_p_neutral,
        "jet": args.iso_min_p_jet,
    }
    ids = [args.event_id] if args.event_id else [r["id"] for r in acc.query(model=args.model, has_bundle=True)]
    results = []
    for event_id in ids:
        try:
            results.append(acc.repack_bundle_selection_ready(
                event_id,
                selection_min_pt=selection_min_pt,
                selection_min_p=selection_min_p,
                prune_bundle=not args.keep_extra_frames,
                bundle_format=args.bundle_format,
            ))
        except Exception as exc:
            results.append({"event_id": event_id, "ok": False, "error": repr(exc)})
    print(json.dumps(results, indent=2))


def _cmd_stats(args) -> None:
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    print(json.dumps(acc.storage_stats(), indent=2))


def _cmd_storage_refresh(args) -> None:
    if not args.events_root:
        raise SystemExit("--events-root is required for storage-refresh")
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    print(json.dumps(acc.refresh_storage_metadata_from_events_root(args.events_root, dry_run=args.dry_run), indent=2))


def _cmd_dashboard_json(args) -> None:
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    payload = acc.dashboard_payload(event_limit=args.limit, include_particles=args.include_particles)
    if args.output_dir and args.output_dir != "out":
        os.makedirs(os.path.dirname(os.path.abspath(args.output_dir)) or ".", exist_ok=True)
        with open(args.output_dir, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"Wrote {args.output_dir}")
    else:
        print(json.dumps(payload, indent=2))


def _cmd_particles(args) -> None:
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    if args.pdg is not None:
        payload = acc.get_particle_info(args.pdg, model=args.model, event_id=args.event_id)
    else:
        payload = acc.list_particles(model=args.model, event_id=args.event_id, include_decays=args.include_decays)
    print(json.dumps(payload, indent=2))


# Backward-compatible alias kept for older scripts/tests.
EventDataBaseManager = EventDatabaseManager


if __name__ == "__main__":
    parser = _build_argparser()
    args = parser.parse_args()
    if args.command == "import":
        if not args.events_root:
            raise SystemExit("--events-root is required for import")
        _cmd_import(args)
    elif args.command == "list":
        _cmd_list(args)
    elif args.command == "show":
        if not args.event_id:
            raise SystemExit("--id is required for show")
        _cmd_show(args)
    elif args.command == "transform":
        if not args.event_id:
            raise SystemExit("--id is required for transform")
        _cmd_transform(args)
    elif args.command == "export-bundle":
        if not args.event_id:
            raise SystemExit("--id is required for export-bundle")
        _cmd_export_bundle(args)
    elif args.command == "repack-selection-ready":
        _cmd_repack_selection_ready(args)
    elif args.command == "stats":
        _cmd_stats(args)
    elif args.command == "storage-refresh":
        _cmd_storage_refresh(args)
    elif args.command == "dashboard-json":
        _cmd_dashboard_json(args)
    elif args.command == "particles":
        _cmd_particles(args)
