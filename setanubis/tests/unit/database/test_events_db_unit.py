import io
import os
import gzip
import json
import sqlite3
import hashlib
import pytest

import SetAnubis.core.DataBase.domain.EventDatabaseManagerv2 as events_mod


def _deterministic_gzip_bytes(payload: bytes) -> bytes:
    bio = io.BytesIO()
    with gzip.GzipFile(fileobj=bio, mode="wb", mtime=0) as gf:
        gf.write(payload)
    return bio.getvalue()


def test_parse_banner_helpers():
    banner = (
        "# Integrated weight (pb) : 1.23e-06\n"
        "BLOCK MASS\n  11 5.110000e-04\n  23 9.118760e+01\n"
        "DECAY 6 1.35e+00\n"
        "import model SM_HeavyN_CKM_AllMasses_LO\n"
        "iseed=424242\n"
    )
    assert events_mod.EventImporter._parse_cross_section(banner) == pytest.approx(1.23e-06)
    masses = events_mod.EventImporter._parse_masses(banner)
    assert masses[11] == pytest.approx(5.11e-04)
    assert masses[23] == pytest.approx(91.1876, rel=1e-6)
    dec = events_mod.EventImporter._parse_decay_info(banner)
    assert dec[6] == pytest.approx(1.35)
    assert events_mod.EventImporter._parse_model(banner) == "SM_HeavyN_CKM_AllMasses_LO"
    assert events_mod.EventImporter._parse_seed(banner) == 424242


def test_scan_base_key_strips_decayed_suffix():
    f = events_mod.EventImporter._scan_base_key
    assert f("run_01_decayed_1") == "run_01"
    assert f("run_01-decayed") == "run_01"
    assert f("plain_run") == "plain_run"


def test_scan_table_parsing_splits_params_and_widths(tmp_path):
    evroot = tmp_path / "Events"; evroot.mkdir()
    scan_txt = (
        "#run_name mass#9900012 numixing#1 cross width#9900012 alpha\n"
        "run_00    5.0e-01     1.0e-03    1.5e-09 8.0e-27       0.118\n"
        "run_01    6.0e-01     2.0e-03    2.5e-09 9.0e-27       0.119\n"
    )
    (evroot / "scan_run_dummy.txt").write_text(scan_txt, encoding="utf-8")
    mapping = events_mod.EventImporter._parse_scan_table(str(evroot))
    assert set(mapping.keys()) == {"run_00", "run_01"}
    r0 = mapping["run_00"]
    assert r0["cross"] == pytest.approx(1.5e-09)
    assert "width#9900012" in r0["widths"] and "width#9900012" not in r0["params"]
    assert "mass#9900012" in r0["params"] and "numixing#1" in r0["params"] and "alpha" in r0["params"]


def test_compute_run_hash_changes_with_content(tmp_path):
    run = tmp_path / "run_00"; run.mkdir()
    (run / "run_01_tag_1_banner.txt").write_text("hello", encoding="utf-8")
    h1 = events_mod.EventImporter._compute_run_hash(str(run))
    (run / "run_01_tag_1_banner.txt").write_text("hello!", encoding="utf-8")
    h2 = events_mod.EventImporter._compute_run_hash(str(run))
    assert h1 != h2


def test_cas_ingest_and_link(tmp_path):
    db_path = tmp_path / "Events.db"
    storage = tmp_path / "Storage"
    db = events_mod.EventDatabaseManager(str(db_path), str(storage), use_hardlinks=False)

    src = tmp_path / "file.bin"
    data = b"ABC" * 50
    src.write_bytes(data)
    sha, size = db._ingest_file_to_cas(str(src))
    assert size == len(data)
    cas_path = db._cas_path(sha)
    assert os.path.exists(cas_path)

    event_folder = os.path.join(db._events_root, "dummy")
    out = db._link_into_event_folder(sha, event_folder, "file.bin")
    assert os.path.exists(out)
    assert open(out, "rb").read() == data

    sha2, _ = db._ingest_file_to_cas(str(src), sha256=sha)
    assert sha2 == sha
    with db._conn() as conn:
        row = conn.execute("SELECT refcount FROM cas_blobs WHERE sha256=?", (sha,)).fetchone()
        assert int(row[0]) >= 2
