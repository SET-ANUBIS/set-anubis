import io
import os
import json
import gzip
import shutil
import sqlite3
import pytest

import SetAnubis.core.DataBase.domain.EventDatabaseManagerv2 as events_mod


def _deterministic_gzip_bytes(payload: bytes) -> bytes:
    bio = io.BytesIO()
    with gzip.GzipFile(fileobj=bio, mode="wb", mtime=0) as gf:
        gf.write(payload)
    return bio.getvalue()


def _mk_run(run_dir, banner_text, lhe_gz_bytes=None, hepmc_gz_bytes=None):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, 'run_01_tag_1_banner.txt'), 'w') as f:
        f.write(banner_text)
    if lhe_gz_bytes is not None:
        with open(os.path.join(run_dir, 'unweighted_events.lhe.gz'), 'wb') as f:
            f.write(lhe_gz_bytes)
    if hepmc_gz_bytes is not None:
        with open(os.path.join(run_dir, 'events.hepmc.gz'), 'wb') as f:
            f.write(hepmc_gz_bytes)


def test_import_two_runs_scan_cas_and_transforms(tmp_path):
    evroot = os.path.join(tmp_path, "Events"); os.makedirs(evroot, exist_ok=True)
    db_path = os.path.join(tmp_path, "Events.db")
    storage_dir = os.path.join(tmp_path, "Storage")

    scan_txt = (
        "#run_name  mass#9900012  numixing#1  cross        width#9900012\n"
        "run_00     5.0e-01       1.0e-06     2.22e-06     9.99e-27\n"
        "run_01     5.0e-01       1.0e+00     1.50e+03     8.97e-15\n"
    )
    with open(os.path.join(evroot, "scan_run_dummy.txt"), "w") as f:
        f.write(scan_txt)

    banner = (
        "# Integrated weight (pb) : 9.99e-06\n"
        "BLOCK MASS\n   6  1.730000e+02\n"
        "DECAY 6 1.35\n"
        "import model SM_HeavyN_CKM_AllMasses_LO\n"
        "iseed=424242\n"
    )

    lhe_gz = _deterministic_gzip_bytes(b"HELLO-LHE-CONTENT")
    lhe_gz_0 = _deterministic_gzip_bytes(b"HELLO-LHE-CONTENT-0")
    lhe_gz_1 = _deterministic_gzip_bytes(b"HELLO-LHE-CONTENT-1")
    hepmc_gz = _deterministic_gzip_bytes(b"HEPMC-CONTENT")

    _mk_run(os.path.join(evroot, "run_00"), banner, lhe_gz_bytes=lhe_gz_0)
    _mk_run(os.path.join(evroot, "run_01"), banner, lhe_gz_bytes=lhe_gz_1)

    db = events_mod.EventDatabaseManager(db_path, storage_dir, use_hardlinks=False)
    importer = events_mod.EventImporter(db)
    acc = events_mod.EventAccessor(db)
    events_mod.register_example_transforms(acc)

    imported = importer.import_from_events_folder(evroot, model="SM_HeavyN_CKM_AllMasses_LO", include_hepmc=False)
    assert len(imported) == 2

    rows = acc.query()
    assert len(rows) == 2
    for r in rows:
        assert r["cross_section"] in (pytest.approx(2.22e-06), pytest.approx(1.50e+03))
        assert r["model"] == "SM_HeavyN_CKM_AllMasses_LO"
        assert r["scan_params_json"]
        params = json.loads(r["scan_params_json"])
        assert "mass#9900012" in params and "numixing#1" in params
        widths = json.loads(r["scan_widths_json"])
        assert "width#9900012" in widths

    first_id = rows[0]["id"]
    arts = acc.get_artifacts(first_id)
    kinds = [a["kind"] for a in arts]
    assert "lhe_gz" in kinds and "banner" in kinds and "hepmc_gz" not in kinds

    with db._conn() as conn:
        blobs = list(conn.execute("SELECT sha256, refcount FROM cas_blobs"))
    assert any(int(rc[1]) >= 2 for rc in blobs)

    imported2 = importer.import_from_events_folder(evroot, model="SM_HeavyN_CKM_AllMasses_LO", include_hepmc=False)
    assert len(imported2) == 0

    out = os.path.join(tmp_path, "out"); os.makedirs(out, exist_ok=True)
    written = events_mod.programmatic_run_transforms(acc, first_id, out)
    assert any(p.endswith(".json") for p in written) and any(p.endswith(".txt") for p in written)

    jpath = [p for p in written if p.endswith(".json")][0]
    payload = json.loads(open(jpath, "r").read())
    assert payload["id"] == first_id
    assert isinstance(payload["artifacts"], list)

    if payload.get("scan_params_json"):
        assert "scan_params" in payload and isinstance(payload["scan_params"], dict)
    if payload.get("scan_widths_json"):
        assert "scan_widths" in payload and isinstance(payload["scan_widths"], dict)


def test_import_with_hepmc_and_query_filters(tmp_path):
    evroot = os.path.join(tmp_path, "Events"); os.makedirs(evroot, exist_ok=True)
    db_path = os.path.join(tmp_path, "Events.db")
    storage_dir = os.path.join(tmp_path, "Storage")

    banner = (
        "# Integrated weight (pb) : 5.0e-03\n"
        "import model MyModel\n"
    )
    lhe_gz = _deterministic_gzip_bytes(b"LHE-DATA")
    hepmc_gz = _deterministic_gzip_bytes(b"HEPMC-DATA")

    _mk_run(os.path.join(evroot, "run_00"), banner, lhe_gz_bytes=lhe_gz, hepmc_gz_bytes=hepmc_gz)

    db = events_mod.EventDatabaseManager(db_path, storage_dir, use_hardlinks=False)
    importer = events_mod.EventImporter(db)
    acc = events_mod.EventAccessor(db)

    imported = importer.import_from_events_folder(evroot, include_hepmc=True)
    assert len(imported) == 1
    eid = imported[0]

    arts = acc.get_artifacts(eid)
    kinds = sorted(a["kind"] for a in arts)
    assert kinds == ["banner", "hepmc_gz", "lhe_gz"]

    rows = acc.query(model="MyModel")
    assert len(rows) == 1 and rows[0]["id"] == eid

    stats = acc.storage_stats()
    assert stats["events"] == 1 and stats["models"] == 1 and stats["cas_blobs"] >= 3
