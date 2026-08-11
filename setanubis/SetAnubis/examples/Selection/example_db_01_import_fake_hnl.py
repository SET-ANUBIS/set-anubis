"""Create a tiny HNL event database from the packaged demonstration HepMC sample."""

from __future__ import annotations

import shutil
from importlib.resources import as_file
from pathlib import Path

from SetAnubis import EventDatabaseManager, EventImporter, SetAnubisInterface, ufo_path
from SetAnubis.examples.Selection.compact_sample import compact_hepmc_resource
from SetAnubis.examples._runtime import run_example_entrypoint

ROOT = Path("outputs/selection_db_demo")
EVENTS = ROOT / "Events"
EVENT_DB = ROOT / "EventsDatabase.db"
EVENT_STORAGE = ROOT / "EventsStorage"
MODEL = "SM_HeavyN_CKM_AllMasses_LO"
CAMPAIGN = "compact_hnl_demo"


def _write_demo_runs() -> None:
    """Build two tiny MadGraph-like run folders around the packaged HepMC file."""
    EVENTS.mkdir(parents=True, exist_ok=True)
    (EVENTS / "scan_run_demo.txt").write_text(
        "#run_name mN1 VeN1 cross width#9900012\n"
        "run_00 1.0 1.0e-6 1.0e-3 1.0e-15\n"
        "run_01 2.0 1.0e-5 1.0e-3 1.0e-15\n",
        encoding="utf-8",
    )

    with as_file(compact_hepmc_resource()) as source_hepmc:
        for index, mass in ((0, 1.0), (1, 2.0)):
            run = EVENTS / f"run_{index:02d}_decayed_1"
            run.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_hepmc, run / "tag_1_pythia8_events.hepmc.gz")
            (run / f"run_{index:02d}_tag_1_banner.txt").write_text(
                "# Integrated weight (pb) : 1.0e-3\n"
                f"import model {MODEL}\n"
                "BLOCK MASS\n"
                f"  9900012  {mass:.8e}\n"
                f"iseed={1000 + index}\n",
                encoding="utf-8",
            )


def main() -> None:
    """Import the two demonstration runs as compact selection-ready bundles."""
    _write_demo_runs()
    db = EventDatabaseManager(str(EVENT_DB), str(EVENT_STORAGE))
    importer = EventImporter(db)

    imported = importer.import_from_events_folder(
        str(EVENTS),
        model=MODEL,
        campaign=CAMPAIGN,
        neo_manager=SetAnubisInterface(ufo_path("UFO_HNL")),
        llp_pid=9900012,
    )
    print(f"Imported {len(imported)} bundle(s) into {EVENT_DB}")


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
