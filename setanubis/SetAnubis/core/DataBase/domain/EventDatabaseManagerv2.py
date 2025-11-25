from __future__ import annotations
import os
import sqlite3
import uuid
import datetime as dt
import shutil
import gzip
import glob
import re
import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple

# -----------------------------
# Constants & Types
# -----------------------------

EventId = str
ModelName = str
ArtifactKind = str  # e.g. "banner", "lhe_gz", "hepmc_gz", "other"
Transform = Callable[["EventAccessor", EventId, str], None]

CAS_DIRNAME = "cas"   # content-addressed storage under storage_dir/cas
EVENTS_DIRNAME = "events"  # human-friendly per-event folders under storage_dir/events

# -----------------------------
# Dataclasses
# -----------------------------

@dataclass
class Event:
    id: EventId
    model: Optional[ModelName]
    date_added: str
    is_decayed: Optional[bool]
    cross_section: Optional[float]
    path: str  # human-facing per-event folder (contains symlinks/notes)
    lhe_sha256: Optional[str]
    hepmc_sha256: Optional[str]
    masses_json: Optional[str]
    seed: Optional[int]
    run_hash: str  # hash of important inputs to dedupe runs
    decay_info_json: Optional[str]
    banner_text: Optional[str]
    # scan-aware fields
    run_name: Optional[str]
    scan_params_json: Optional[str]
    scan_widths_json: Optional[str]

# -----------------------------
# Database Layer
# -----------------------------

class EventDatabaseManager:
    """SQLite manager with content-addressed storage (CAS) for large files.
    - Single copy per unique SHA-256
    - Per-event folder contains symlinks (or hardlinks) to CAS blobs
    """

    def __init__(self, db_path: str = "db/EventsDatabase.db", storage_dir: str = "db/EventsStorage", use_hardlinks: bool = False):
        self.db_path = db_path
        self.storage_dir = storage_dir
        self.use_hardlinks = use_hardlinks
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self._cas_root, exist_ok=True)
        os.makedirs(self._events_root, exist_ok=True)
        self._init_db()

    # --- Paths
    @property
    def _cas_root(self) -> str:
        return os.path.join(self.storage_dir, CAS_DIRNAME)

    @property
    def _events_root(self) -> str:
        return os.path.join(self.storage_dir, EVENTS_DIRNAME)

    # --- DB init & migration helpers
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
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
                    scan_widths_json TEXT
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
            # Indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_model ON events(model_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_event ON artifacts(event_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_sha ON artifacts(sha256);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_run_name ON events(run_name);")
            # Migrate existing DBs missing new columns
            self._ensure_event_columns(conn, ["run_name", "scan_params_json", "scan_widths_json"]) 

    @staticmethod
    def _ensure_event_columns(conn: sqlite3.Connection, columns: List[str]) -> None:
        cur = conn.execute("PRAGMA table_info(events)")
        existing = {row[1] for row in cur.fetchall()}
        for col in columns:
            if col not in existing:
                conn.execute(f"ALTER TABLE events ADD COLUMN {col} TEXT")

    # --- Models
    def _get_or_create_model_id(self, name: Optional[str]) -> Optional[int]:
        if not name:
            return None
        with self._conn() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM models WHERE name=?", (name,))
            row = c.fetchone()
            if row:
                return int(row[0])
            c.execute("INSERT INTO models(name) VALUES (?)", (name,))
            return int(c.lastrowid)

    # --- CAS helpers
    def _cas_path(self, sha256: str) -> str:
        return os.path.join(self._cas_root, sha256[:2], sha256)

    def _ensure_cas_dirs(self, sha256: str) -> None:
        os.makedirs(os.path.dirname(self._cas_path(sha256)), exist_ok=True)

    def _ingest_file_to_cas(self, src: str, sha256: Optional[str] = None) -> Tuple[str, int]:
        if sha256 is None:
            h = hashlib.sha256()
            with open(src, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            sha256 = h.hexdigest()
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

    def _link_into_event_folder(self, sha256: str, event_folder: str, filename: str) -> str:
        os.makedirs(event_folder, exist_ok=True)
        cas_file = self._cas_path(sha256)
        target = os.path.join(event_folder, filename)
        if os.path.exists(target):
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

# -----------------------------
# Importer & Parsers
# -----------------------------

class EventImporter:
    def __init__(self, db: EventDatabaseManager):
        self.db = db

    # --- Public API
    def import_from_events_folder(self, events_folder: str, *, model: Optional[str] = None, include_hepmc: bool = True) -> List[EventId]:
        scan_map = self._parse_scan_table(events_folder)
        run_folders = [
            os.path.join(events_folder, d)
            for d in os.listdir(events_folder)
            if os.path.isdir(os.path.join(events_folder, d))
        ]
        imported: List[EventId] = []
        for run in sorted(run_folders):
            ev = self._import_single_run(run, model=model, include_hepmc=include_hepmc, scan_map=scan_map)
            if ev:
                imported.append(ev)
        return imported

    # --- Core import
    def _import_single_run(self, run_folder: str, *, model: Optional[str], include_hepmc: bool, scan_map: Dict[str, Dict[str, Any]]) -> Optional[EventId]:
        """Import one MadGraph run folder.
        Uses scan_map to attach per-run parameters:
          - cross_section: scan.cross (fallback banner)
          - scan_params_json: all scan columns EXCEPT run_name/cross/width*
          - scan_widths_json: ONLY width* columns (e.g. width#9900012)
        """
        run_hash = self._compute_run_hash(run_folder)
        with self.db._conn() as conn:
            cur = conn.execute("SELECT id FROM events WHERE run_hash=?", (run_hash,))
            row = cur.fetchone()
            if row:
                print(f"Run {run_folder} already imported as {row['id']}. Skipping.")
                return None
        
        run_name = os.path.basename(run_folder.rstrip(os.sep))
        scan_key = self._scan_base_key(run_name)
        scan_row = (scan_map.get(run_name) or scan_map.get(scan_key) or {}) if scan_map else {}
        # scan_row = scan_map.get(run_name, {}) if scan_map else {}
        cross_from_scan = scan_row.get("cross")
        scan_params = scan_row.get("params", {})
        scan_widths = scan_row.get("widths", {})

        event_id = str(uuid.uuid4())
        event_folder = os.path.join(self.db._events_root, event_id)
        os.makedirs(event_folder, exist_ok=True)

        # discover files
        all_files = glob.glob(os.path.join(run_folder, "*"))
        banner_file = next((f for f in all_files if re.search(r"banner", os.path.basename(f), re.I)), None)
        lhe_file = next((f for f in all_files if re.search(r"\.lhe(\.gz)?$", os.path.basename(f), re.I)), None)
        hepmc_file = next((f for f in all_files if re.search(r"\.hepmc(\.gz)?$", os.path.basename(f), re.I)), None)

        # parse banner (if any)
        banner_text = ""
        if banner_file and os.path.exists(banner_file):
            with open(banner_file, "r", errors="ignore") as f:
                banner_text = f.read()

        cross_banner = self._parse_cross_section(banner_text)
        masses = self._parse_masses(banner_text)
        seed = self._parse_seed(banner_text)
        decay_info = self._parse_decay_info(banner_text)
        detected_model = self._parse_model(banner_text) or model
        is_decayed = bool(re.search(r"decayed", run_folder, re.I))

        cross_section = cross_from_scan if cross_from_scan is not None else cross_banner

        # Ingest files -> CAS (don't record artifacts before event insert)
        lhe_sha256 = None; lhe_filename = None; lhe_size = None
        if lhe_file:
            if lhe_file.endswith(".gz"):
                lhe_sha256, lhe_size = self._ingest_to_cas(lhe_file)
                lhe_filename = os.path.basename(lhe_file)
            else:
                gz_name = os.path.basename(lhe_file) + ".gz"
                gz_tmp = os.path.join(event_folder, gz_name)
                with open(lhe_file, "rb") as fin, gzip.open(gz_tmp, "wb") as fout:
                    shutil.copyfileobj(fin, fout)
                lhe_sha256, lhe_size = self._ingest_to_cas(gz_tmp)
                os.remove(gz_tmp)
                lhe_filename = gz_name

        hepmc_sha256 = None; hepmc_filename = None; hepmc_size = None
        if include_hepmc and hepmc_file:
            if hepmc_file.endswith(".gz"):
                hepmc_sha256, hepmc_size = self._ingest_to_cas(hepmc_file)
                hepmc_filename = os.path.basename(hepmc_file)
            else:
                gz_name = os.path.basename(hepmc_file) + ".gz"
                gz_tmp = os.path.join(event_folder, gz_name)
                with open(hepmc_file, "rb") as fin, gzip.open(gz_tmp, "wb") as fout:
                    shutil.copyfileobj(fin, fout)
                hepmc_sha256, hepmc_size = self._ingest_to_cas(gz_tmp)
                os.remove(gz_tmp)
                hepmc_filename = gz_name

        # Insert event row now (satisfy FK for artifacts)
        with self.db._conn() as conn:
            model_id = self._get_or_create_model_id_cached(conn, detected_model)
            conn.execute(
                """
                INSERT INTO events (
                    id, model_id, date_added, is_decayed, cross_section, path,
                    lhe_sha256, hepmc_sha256, masses_json, seed, run_hash,
                    decay_info_json, banner_text, run_name, scan_params_json, scan_widths_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    event_id,
                    model_id,
                    dt.datetime.now().isoformat(),
                    int(is_decayed) if is_decayed is not None else None,
                    cross_section,
                    event_folder,
                    lhe_sha256,
                    hepmc_sha256,
                    json.dumps(masses) if masses else None,
                    seed,
                    run_hash,
                    json.dumps(decay_info) if decay_info else None,
                    banner_text or None,
                    run_name,
                    json.dumps(scan_params) if scan_params else None,
                    json.dumps(scan_widths) if scan_widths else None,
                ),
            )

        if lhe_sha256 and lhe_filename:
            self._record_artifact(event_id, "lhe_gz", lhe_sha256, lhe_filename, int(lhe_size or 0))
            self.db._link_into_event_folder(lhe_sha256, event_folder, lhe_filename)
        if hepmc_sha256 and hepmc_filename:
            self._record_artifact(event_id, "hepmc_gz", hepmc_sha256, hepmc_filename, int(hepmc_size or 0))
            self.db._link_into_event_folder(hepmc_sha256, event_folder, hepmc_filename)
        if banner_file:
            sha, size = self._ingest_to_cas(banner_file)
            self._record_artifact(event_id, "banner", sha, os.path.basename(banner_file), size)
            self.db._link_into_event_folder(sha, event_folder, os.path.basename(banner_file))

        print(f"Imported event {event_id} (run={run_name}, model={detected_model}, decayed={is_decayed})")
        return event_id

    @staticmethod
    def _scan_base_key(run_name_or_folder: str) -> str:
        name = os.path.basename(run_name_or_folder.rstrip(os.sep))
        return re.sub(r'(_|-)?decayed.*$', '', name, flags=re.I)

    # --- Small wrappers for readability
    def _ingest_to_cas(self, path: str) -> Tuple[str, int]:
        return self.db._ingest_file_to_cas(path)

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

    # --- Parsers (static)
    @staticmethod
    def _parse_cross_section(banner_text: str) -> Optional[float]:
        m = re.search(r"#\s*Integrated weight \(pb\)\s*:\s*([\d\.eE\-]+)", banner_text)
        return float(m.group(1)) if m else None

    @staticmethod
    def _parse_masses(banner_text: str) -> Dict[int, float]:
        masses: Dict[int, float] = {}
        m = re.search(r"BLOCK\s+MASS(.*?)(?:BLOCK|$)", banner_text, re.S | re.I)
        if not m:
            return masses
        for line in m.group(1).splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0].lstrip("-+").isdigit():
                try:
                    pdg = int(parts[0]); val = float(parts[1])
                    masses[pdg] = val
                except ValueError:
                    pass
        return masses

    @staticmethod
    def _parse_decay_info(banner_text: str) -> Dict[int, float]:
        info: Dict[int, float] = {}
        for pdg, width in re.findall(r"DECAY\s+(\d+)\s+([\d\.eE\-\+]+)", banner_text):
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
        m = re.search(r"iseed\s*=\s*(\d+)", banner_text)
        return int(m.group(1)) if m else None

    @staticmethod
    def _compute_run_hash(run_folder: str) -> str:
        h = hashlib.sha256()
        important = [
            "params.dat",
            "unweighted_events.lhe",
            "unweighted_events.lhe.gz",
            "run_01_tag_1_banner.txt",
            "run_01_decayed_1_tag_1_banner.txt",
        ]
        for fname in important:
            path = os.path.join(run_folder, fname)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
        return h.hexdigest()

    # --- Scan table parser
    @staticmethod
    def _parse_scan_table(events_folder: str) -> Dict[str, Dict[str, Any]]:
        """Parse Events/scan_run*.txt → mapping by run_name with separated params/widths.
        Output structure per run:
          {
            'run_name': 'run_01',
            'cross': <float|None>,
            'params': {<k>: <v>, ...},    # excludes 'cross' and any 'width*'
            'widths': {<k>: <v>, ...}     # only columns starting with 'width'
          }
        """
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
                if line.lstrip().startswith('#'):
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
                # normalize & split into cross / params / widths
                cross_val: Optional[float] = None
                params: Dict[str, Any] = {}
                widths: Dict[str, Any] = {}
                for k, v in row.items():
                    if k in ("run_name", "run", "name"):
                        continue
                    # try float conversion
                    try:
                        num = float(v)
                    except Exception:
                        num = v
                    if k.lower() == 'cross':
                        cross_val = num if isinstance(num, float) else None
                        continue
                    if k.lower().startswith('width'):
                        widths[k] = num
                    else:
                        params[k] = num
                mapping[run] = {
                    'run_name': run,
                    'cross': cross_val,
                    'params': params,
                    'widths': widths,
                }
        print(f"Parsed scan table from {os.path.basename(path)} with {len(mapping)} entries")
        return mapping

    # --- tiny cache for model_id during single import
    def _get_or_create_model_id_cached(self, conn: sqlite3.Connection, name: Optional[str]) -> Optional[int]:
        if not name:
            return None
        cur = conn.execute("SELECT id FROM models WHERE name=?", (name,))
        row = cur.fetchone()
        if row:
            return int(row[0])
        cur = conn.execute("INSERT INTO models(name) VALUES (?)", (name,))
        return int(cur.lastrowid)

# -----------------------------
# Access layer & transforms
# -----------------------------

class EventAccessor:
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

    def query(self, *, model: Optional[str] = None, where: str = "", params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        sql = (
            "SELECT e.*, m.name as model FROM events e "
            "LEFT JOIN models m ON e.model_id=m.id WHERE 1=1"
        )
        args: List[Any] = []
        if model:
            sql += " AND m.name=?"; args.append(model)
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
        return Event(
            id=row['id'],
            model=row['model'],
            date_added=row['date_added'],
            is_decayed=bool(row['is_decayed']) if row['is_decayed'] is not None else None,
            cross_section=row['cross_section'],
            path=row['path'],
            lhe_sha256=row['lhe_sha256'],
            hepmc_sha256=row['hepmc_sha256'],
            masses_json=row['masses_json'],
            seed=row['seed'],
            run_hash=row['run_hash'],
            decay_info_json=row['decay_info_json'],
            banner_text=row['banner_text'],
            run_name=row['run_name'],
            scan_params_json=row['scan_params_json'],
            scan_widths_json=row['scan_widths_json'],
        )

    def get_artifacts(self, event_id: str) -> List[sqlite3.Row]:
        with self.db._conn() as conn:
            return list(conn.execute(
                "SELECT kind, sha256, filename, size_bytes FROM artifacts WHERE event_id=? ORDER BY kind",
                (event_id,),
            ))

    def artifact_path(self, sha256: str) -> str:
        return self.db._cas_path(sha256)

    def storage_stats(self) -> Dict[str, Any]:
        with self.db._conn() as conn:
            blobs = conn.execute("SELECT COUNT(*), SUM(size_bytes) FROM cas_blobs").fetchone()
            events = conn.execute("SELECT COUNT(*) FROM events").fetchone()
            models = conn.execute("SELECT COUNT(*) FROM models").fetchone()
        return {
            'events': int(events[0] or 0),
            'models': int(models[0] or 0),
            'cas_blobs': int(blobs[0] or 0),
            'cas_size_bytes': int(blobs[1] or 0),
        }

# -----------------------------
# Example transforms
# -----------------------------

def register_example_transforms(accessor: EventAccessor) -> None:
    accessor.register_transform('to_json', _transform_to_json)
    accessor.register_transform('report_txt', _transform_report_txt)


def _transform_to_json(acc: EventAccessor, event_id: str, output_dir: str) -> None:
    ev = acc.get_event(event_id)
    if not ev:
        raise ValueError(f"Event {event_id} not found")
    artifacts = [dict(row) for row in acc.get_artifacts(event_id)]
    payload = asdict(ev)
    # decode the JSON-encoded fields for convenience
    for field in ('scan_params_json', 'scan_widths_json'):
        if payload.get(field):
            try:
                payload[field.replace('_json', '')] = json.loads(payload[field])
            except Exception:
                payload[field.replace('_json', '')] = None
    out_path = os.path.join(output_dir, f"{event_id}.json")
    with open(out_path, 'w') as f:
        json.dump({**payload, 'artifacts': artifacts}, f, indent=2)
    print(f"Wrote {out_path}")


def _transform_report_txt(acc: EventAccessor, event_id: str, output_dir: str) -> None:
    ev = acc.get_event(event_id)
    if not ev:
        raise ValueError(f"Event {event_id} not found")
    scan_params = {}
    scan_widths = {}
    if ev.scan_params_json:
        try: scan_params = json.loads(ev.scan_params_json)
        except Exception: pass
    if ev.scan_widths_json:
        try: scan_widths = json.loads(ev.scan_widths_json)
        except Exception: pass
    lines = [
        f"Event: {ev.id}",
        f"Run: {ev.run_name}",
        f"Model: {ev.model}",
        f"Date: {ev.date_added}",
        f"Decayed: {ev.is_decayed}",
        f"Cross-section (pb): {ev.cross_section}",
        f"Seed: {ev.seed}",
        f"Scan params: {scan_params}",
        f"Scan widths: {scan_widths}",
    ]
    out_path = os.path.join(output_dir, f"{event_id}.txt")
    with open(out_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"Wrote {out_path}")

# -----------------------------
# Programmatic test mains (no CLI)
# -----------------------------

def programmatic_import(events_root: str, model: Optional[str] = None, *, include_hepmc: bool = False,
                        db_path: str = 'db/EventsDatabase.db', storage_dir: str = 'db/EventsStorage'):
    db = EventDatabaseManager(db_path, storage_dir)
    importer = EventImporter(db)
    acc = EventAccessor(db)
    register_example_transforms(acc)
    imported = importer.import_from_events_folder(events_root, model=model, include_hepmc=include_hepmc)
    return db, importer, acc, imported


def programmatic_list(acc: EventAccessor, *, model: Optional[str] = None):
    return acc.query(model=model)


def programmatic_show(acc: EventAccessor, event_id: str) -> dict:
    ev = acc.get_event(event_id)
    arts = acc.get_artifacts(event_id)
    payload = asdict(ev) if ev else None
    if payload and payload.get('scan_params_json'):
        try: payload['scan_params'] = json.loads(payload['scan_params_json'])
        except Exception: pass
    if payload and payload.get('scan_widths_json'):
        try: payload['scan_widths'] = json.loads(payload['scan_widths_json'])
        except Exception: pass
    return {'event': payload, 'artifacts': [dict(a) for a in arts]}


def programmatic_run_transforms(acc: EventAccessor, event_id: str, out_dir: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name in acc.available_transforms():
        acc.run_transform(event_id, name, out_dir)
        if name == 'to_json':
            written.append(os.path.join(out_dir, f'{event_id}.json'))
        elif name == 'report_txt':
            written.append(os.path.join(out_dir, f'{event_id}.txt'))
    return written


def programmatic_demo() -> dict:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        evroot = os.path.join(tmp, 'Events')
        os.makedirs(evroot, exist_ok=True)
        # Scan with width columns; these will go to scan_widths_json, NOT scan_params_json
        scan_txt = (
            "#run_name            mass#9900012         numixing#1           cross                width#9900012\n"
            "run_00               5.000000e-01         1.000000e-06         1.516223e-09         8.979284e-27\n"
            "run_01               5.000000e-01         1.000000e+00         1.504185e+03         8.979284e-15\n"
        )
        with open(os.path.join(evroot, 'scan_run_dummy.txt'), 'w') as f:
            f.write(scan_txt)
        banner = (
            "# Integrated weight (pb) : 9.99e-06\n"
            "BLOCK MASS\n   6  1.730000e+02\n"
            "DECAY 6 1.35\n"
            "import model SM_HeavyN_CKM_AllMasses_LO\n"
            "iseed=424242\n"
        )
        for i in range(2):
            run = os.path.join(evroot, f'run_{i:02d}')
            os.makedirs(run, exist_ok=True)
            with open(os.path.join(run, 'run_01_tag_1_banner.txt'), 'w') as f:
                f.write(banner)
            with open(os.path.join(run, 'unweighted_events.lhe'), 'wb') as f:
                f.write(os.urandom(1024 + i))
        db_path = os.path.join(tmp, 'EventsDatabase.db')
        storage_dir = os.path.join(tmp, 'EventsStorage')
        db, importer, acc, imported = programmatic_import(evroot, model='SM_HeavyN_CKM_AllMasses_LO', include_hepmc=False, db_path=db_path, storage_dir=storage_dir)
        rows = programmatic_list(acc)
        first_id = rows[0]['id'] if rows else None
        out_dir = os.path.join(tmp, 'out')
        written = []
        if first_id:
            written = programmatic_run_transforms(acc, first_id, out_dir)
        return {
            'tmp': tmp,
            'db_path': db_path,
            'storage_dir': storage_dir,
            'imported': imported,
            'rows': [dict(r) for r in rows],
            'first_id': first_id,
            'written': written,
            'stats': acc.storage_stats(),
        }

# -----------------------------
# CLI / Test mains
# -----------------------------

TEST_HELP = """
Examples:
  python events_db_optimized_scanaware_v2.py import --events-root db/Temp/madgraph/Events/Events --model SM_HeavyN_CKM_AllMasses_LO --skip-hepmc
  python events_db_optimized_scanaware_v2.py list --model SM_HeavyN_CKM_AllMasses_LO
  python events_db_optimized_scanaware_v2.py show --id <EVENT_UUID>
  python events_db_optimized_scanaware_v2.py transform --id <EVENT_UUID> --name to_json --out out
  python events_db_optimized_scanaware_v2.py stats
"""

def _build_argparser():
    import argparse
    p = argparse.ArgumentParser(description='Events DB manager (scan-aware widths separated) with CAS + transforms', epilog=TEST_HELP, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('command', choices=['import', 'list', 'show', 'transform', 'stats', 'demo'])
    p.add_argument('--db', dest='db_path', default='db/EventsDatabase.db')
    p.add_argument('--storage', dest='storage_dir', default='db/EventsStorage')
    p.add_argument('--hardlinks', action='store_true')
    p.add_argument('--events-root', dest='events_root')
    p.add_argument('--model', dest='model')
    p.add_argument('--skip-hepmc', action='store_true')
    p.add_argument('--id', dest='event_id')
    p.add_argument('--name', dest='transform_name')
    p.add_argument('--out', dest='output_dir', default='out')
    return p

def _cmd_import(args):
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    importer = EventImporter(db)
    acc = EventAccessor(db)
    register_example_transforms(acc)
    include_hepmc = not args.skip_hepmc
    imported = importer.import_from_events_folder(args.events_root, model=args.model, include_hepmc=include_hepmc)
    print(f'Imported {len(imported)} events')

def _cmd_list(args):
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    rows = acc.query(model=args.model)
    for r in rows:
        print(f"{r['id']} | run={r['run_name']} | model={r['model']} | xsec={r['cross_section']} pb | decayed={r['is_decayed']} | date={r['date_added']}")
    print(f'Total: {len(rows)} events')

def _cmd_show(args):
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    ev = acc.get_event(args.event_id)
    if not ev:
        print('Event not found'); return
    payload = asdict(ev)
    if payload.get('scan_params_json'):
        try: payload['scan_params'] = json.loads(payload['scan_params_json'])
        except Exception: pass
    if payload.get('scan_widths_json'):
        try: payload['scan_widths'] = json.loads(payload['scan_widths_json'])
        except Exception: pass
    print(json.dumps(payload, indent=2))
    arts = acc.get_artifacts(args.event_id)
    if arts:
        print('Artifacts:')
        for a in arts:
            print(f"  - {a['kind']}: {a['filename']} ({a['size_bytes']} B) -> {acc.artifact_path(a['sha256'])}")

def _cmd_transform(args):
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    register_example_transforms(acc)
    if args.transform_name is None:
        print('Available:', ', '.join(acc.available_transforms())); return
    acc.run_transform(args.event_id, args.transform_name, args.output_dir)

def _cmd_stats(args):
    db = EventDatabaseManager(args.db_path, args.storage_dir, use_hardlinks=args.hardlinks)
    acc = EventAccessor(db)
    print(json.dumps(acc.storage_stats(), indent=2))

def _cmd_demo(args):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        evroot = os.path.join(tmp, 'Events'); os.makedirs(evroot, exist_ok=True)
        scan_txt = (
            "#run_name            mass#9900012         numixing#1           cross                width#9900012\n"
            "run_01               5.000000e-01         1.000000e-06         1.516223e-09         8.979284e-27\n"
            "run_02               5.000000e-01         1.000000e+00         1.504185e+03         8.979284e-15\n"
        )
        with open(os.path.join(evroot, 'scan_run_dummy.txt'), 'w') as f: f.write(scan_txt)
        banner = (
            "# Integrated weight (pb) : 1.23e-06\n"
            "BLOCK MASS\n   6  1.730000e+02\n"
            "DECAY 6 1.35\n"
            "import model SM_HeavyN_CKM_AllMasses_LO\n"
            "iseed=424242\n"
        )
        for i in range(2):
            run = os.path.join(evroot, f'run_{i+1:02d}'); os.makedirs(run, exist_ok=True)
            with open(os.path.join(run, 'run_01_tag_1_banner.txt'), 'w') as f: f.write(banner)
            with open(os.path.join(run, 'unweighted_events.lhe'), 'wb') as f: f.write(os.urandom(1024 + i))
        db_path = os.path.join(tmp, 'EventsDatabase.db'); storage_dir = os.path.join(tmp, 'EventsStorage')
        db = EventDatabaseManager(db_path, storage_dir); importer = EventImporter(db); acc = EventAccessor(db)
        register_example_transforms(acc)
        imported = importer.import_from_events_folder(evroot, model='SM_HeavyN_CKM_AllMasses_LO', include_hepmc=False)
        print(f'Imported {len(imported)} events into {db_path}')
        for row in acc.query():
            print(f"- {row['id']} run={row['run_name']} xsec={row['cross_section']} pb model={row['model']}")
        if imported:
            eid = imported[0]
            _cmd_show(_mk_ns(db_path, storage_dir, eid))
            out = os.path.join(tmp, 'out'); acc.run_transform(eid, 'to_json', out); acc.run_transform(eid, 'report_txt', out)
            print('Demo out dir:', out)
        print('Stats:', json.dumps(acc.storage_stats(), indent=2))

def _mk_ns(db, storage, event_id):
    class _NS: pass
    ns = _NS(); ns.db_path = db; ns.storage_dir = storage; ns.hardlinks = False; ns.event_id = event_id; return ns

if __name__ == '__main__':
    p = _build_argparser(); args = p.parse_args()
    if args.command == 'import':
        if not args.events_root: raise SystemExit('--events-root is required for import')
        _cmd_import(args)
    elif args.command == 'list': _cmd_list(args)
    elif args.command == 'show':
        if not args.event_id: raise SystemExit('--id is required for show')
        _cmd_show(args)
    elif args.command == 'transform':
        if not args.event_id: raise SystemExit('--id is required for transform')
        _cmd_transform(args)
    elif args.command == 'stats': _cmd_stats(args)
    elif args.command == 'demo': _cmd_demo(args)
