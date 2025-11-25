import os
import sqlite3
import uuid
import datetime
import shutil
import gzip
import glob
import re
import hashlib
import json

from enum import IntEnum

class EventFields(IntEnum):
    ID = 0
    DATE_ADDED = 1
    IS_DECAYED = 2
    CROSS_SECTION = 3
    PATH = 4
    LHE_FILE = 5
    HEPMC_FILE = 6
    MASSES = 7
    SEED = 8
    HASH = 9
    
class EventDatabaseManager:
    def __init__(self, db_path="db/EventsDatabase.db", storage_dir="db/EventsStorage"):
        self.db_path = db_path
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                date_added TEXT,
                is_decayed BOOLEAN,
                cross_section REAL,
                path TEXT,
                lhe_file TEXT,
                hepmc_file TEXT,
                masses TEXT,
                seed INTEGER,
                hash TEXT UNIQUE,
                decay_info TEXT,
                model TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def add_event(self, event_metadata):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO events (id, date_added, is_decayed, cross_section, path, lhe_file, hepmc_file, masses, seed, hash, decay_info, model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_metadata['id'],
                event_metadata['date_added'],
                event_metadata['is_decayed'],
                event_metadata['cross_section'],
                event_metadata['path'],
                event_metadata['lhe_file'],
                event_metadata['hepmc_file'],
                json.dumps(event_metadata['masses']),
                event_metadata['seed'],
                event_metadata['hash'],
                event_metadata['decay_info'],
                event_metadata['model']
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            print(f"Event with hash {event_metadata['hash']} already exists. Skipping.")
        finally:
            conn.close()

class EventImporter:
    def __init__(self, db_manager: EventDatabaseManager):
        self.db_manager = db_manager

    def import_from_events_folder(self, events_folder):
        run_folders = [os.path.join(events_folder, d) for d in os.listdir(events_folder) if os.path.isdir(os.path.join(events_folder, d))]

        for run_folder in run_folders:
            self._import_single_run(run_folder)

    def _import_single_run(self, run_folder):
        run_hash = self.compute_run_hash(run_folder)

        conn = sqlite3.connect(self.db_manager.db_path)
        c = conn.cursor()
        c.execute('SELECT id FROM events WHERE hash=?', (run_hash,))
        if c.fetchone():
            print(f"Run {run_folder} already imported. Skipping.")
            conn.close()
            return
        conn.close()

        event_id = str(uuid.uuid4())
        target_dir = os.path.join(self.db_manager.storage_dir, event_id)
        os.makedirs(target_dir, exist_ok=True)

        for file in glob.glob(os.path.join(run_folder, '*')):
            shutil.copy(file, target_dir)

        banner_file = next((f for f in os.listdir(target_dir) if 'banner' in f), None)
        lhe_file = next((f for f in os.listdir(target_dir) if f.endswith('.lhe') or f.endswith('.lhe.gz')), None)
        hepmc_file = next((f for f in os.listdir(target_dir) if f.endswith('.hepmc.gz')), None)

        if lhe_file and lhe_file.endswith('.lhe'):
            original_path = os.path.join(target_dir, lhe_file)
            compressed_path = original_path + ".gz"
            with open(original_path, 'rb') as f_in, gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            os.remove(original_path)
            lhe_file = os.path.basename(compressed_path)

        banner_text = ""
        if banner_file:
            with open(os.path.join(target_dir, banner_file), 'r') as f:
                banner_text = f.read()

        cross_section = self._parse_cross_section(banner_text)
        masses = self._parse_masses(banner_text)
        seed = self._parse_seed(banner_text)
        is_decayed = 'decayed' in run_folder.lower()
        decay_info = self._parse_decay_info(banner_text)
        model = self._parse_model(banner_text)

        metadata = {
            'id': event_id,
            'date_added': datetime.datetime.now().isoformat(),
            'is_decayed': is_decayed,
            'cross_section': cross_section,
            'path': target_dir,
            'lhe_file': lhe_file,
            'hepmc_file': hepmc_file,
            'masses': masses,
            'seed': seed,
            'hash': run_hash,
            'decay_info': json.dumps(decay_info),
            'model': model
        }
        print(metadata)
        self.db_manager.add_event(metadata)

    def _parse_cross_section(self, banner_text):
        match = re.search(r"#\s*Integrated weight \(pb\)\s*:\s*([\d\.eE\-]+)", banner_text)
        return float(match.group(1)) if match else None

    def _parse_masses(self, banner_text):
        masses = {}
        block_mass_match = re.search(r"BLOCK MASS(.*?)BLOCK", banner_text, re.DOTALL | re.IGNORECASE)
        if block_mass_match:
            lines = block_mass_match.group(1).splitlines()
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        pdg_id = int(parts[0])
                        mass_value = float(parts[1])
                        masses[pdg_id] = mass_value
                    except ValueError:
                        continue
        return masses

    def _parse_decay_info(self, banner_text):
        decay_blocks = re.findall(r'DECAY\s+(\d+)\s+([\d\.eE\-\+]+)', banner_text)
        decay_info = {}
        for pdg_id, width in decay_blocks:
            decay_info[int(pdg_id)] = float(width)
        return decay_info

    def _parse_model(self, banner_text):
        matches = re.findall(r'import model (\S+)', banner_text)
        for model_name in matches:
            if model_name.lower() != "sm":
                return model_name
        return None

    def _parse_seed(self, banner_text):
        match = re.search(r"iseed\s*=\s*(\d+)", banner_text)
        return int(match.group(1)) if match else None

    def compute_run_hash(self, run_folder):
        hash_sha256 = hashlib.sha256()
        important_files = ['params.dat', 'unweighted_events.lhe', 'unweighted_events.lhe.gz', 'run_01_tag_1_banner.txt', 'run_01_decayed_1_tag_1_banner.txt']
        for filename in important_files:
            path = os.path.join(run_folder, filename)
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    while chunk := f.read(8192):
                        hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

class EventAccessor:
    def __init__(self, db_manager: EventDatabaseManager):
        self.db_manager = db_manager

    def query(self, filters=None):
        conn = sqlite3.connect(self.db_manager.db_path)
        c = conn.cursor()
        query = "SELECT * FROM events WHERE 1=1"
        values = []
        if filters:
            for key, value in filters.items():
                query += f" AND {key}=?"
                values.append(value)
        c.execute(query, values)
        results = c.fetchall()
        conn.close()
        return results

    def get_param(self, event_id, param):
        conn = sqlite3.connect(self.db_manager.db_path)
        c = conn.cursor()
        c.execute(f"SELECT {param} FROM events WHERE id=?", (event_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def query_by_model(self, model_name):
        return self.query(filters={"model": model_name})

if __name__=="__main__":
    db_manager = EventDatabaseManager()

    importer = EventImporter(db_manager)
    importer.import_from_events_folder('db/Temp/madgraph/Events/Events')

    accessor = EventAccessor(db_manager)

    print("All events:")
    events = accessor.query()
    for event in events:
        print(f"ID: {event[EventFields.ID]}, Date: {event[EventFields.DATE_ADDED]}, Cross-section: {event[EventFields.CROSS_SECTION]} pb")

    print("\nEvents with cross-section > 1e-8 pb:")
    for event in events:
        if event[EventFields.CROSS_SECTION] and event[EventFields.CROSS_SECTION] > 1e-8:
            print(f"ID: {event[EventFields.ID]}, Cross-section: {event[EventFields.CROSS_SECTION]} pb")

    if events:
        event_id = events[0][EventFields.ID]
        masses_json = accessor.get_param(event_id, 'masses')
        masses = json.loads(masses_json)
        print(f"\nMasses for event {event_id}:")
        for pdg, mass in masses.items():
            print(f"PDG ID {pdg}: mass {mass} GeV")

    print("\nChecking decayed status:")
    for event in events:
        print(f"ID: {event[EventFields.ID]}, Decayed: {bool(event[EventFields.IS_DECAYED])}")

    print("\nPaths to LHE and HEPMC files:")
    for event in events:
        path = event[EventFields.PATH]
        lhe = event[EventFields.LHE_FILE]
        hepmc = event[EventFields.HEPMC_FILE]
        print(f"Event {event[EventFields.ID]}: LHE: {os.path.join(path, lhe)}", end="")
        if hepmc:
            print(f", HEPMC: {os.path.join(path, hepmc)}")
        else:
            print(", HEPMC: None")
            
    model_name = "SM_HeavyN_CKM_AllMasses_LO"
    print(f"\Events for model '{model_name}':")
    events = accessor.query_by_model(model_name)
    for event in events:
        print(f"ID: {event[EventFields.ID]}, Cross-section: {event[EventFields.CROSS_SECTION]} pb")

    if events:
        event_id = events[0][EventFields.ID]
        decay_info_json = accessor.get_param(event_id, 'decay_info')
        decay_info = json.loads(decay_info_json)
        print(f"\nDECAY pour l'événement {event_id}:")
        for pdg_id, width in decay_info.items():
            print(f"PDG ID {pdg_id}: Width {width} GeV")