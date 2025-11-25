import json
import yaml
from pathlib import Path
import pytest

import SetAnubis.core.BranchingRatio.domain.MartyUtil as marty_mod


def test_loader_reads_json_and_yaml_and_merges(tmp_path: Path, monkeypatch):
    assets = tmp_path / "Assets" / "MARTY" / "model"
    assets.mkdir(parents=True, exist_ok=True)

    # JSON
    (assets / "conversion_sm.json").write_text(
        json.dumps([
            {"name": "alpha0", "ufo_name": "aEWM1"},
            {"name": "keep_same", "ufo_name": "keep_same"},
        ]),
        encoding="utf-8",
    )

    # YAML
    (assets / "conversion_model.yaml").write_text(
        yaml.safe_dump([
            {"name": "Ve1", "ufo_name": "Ve1"},
            {"name": "override_me", "ufo_name": "OVR"},
        ]),
        encoding="utf-8",
    )

    def local_loader(reversed: bool):
        mapping = {}
        json_file = assets / "conversion_sm.json"
        yaml_file = assets / "conversion_model.yaml"
        if json_file.exists():
            data = json.loads(json_file.read_text())
            mapping.update({e["name"]: e["ufo_name"] for e in data if "name" in e and "ufo_name" in e})
        if yaml_file.exists():
            data = yaml.safe_load(yaml_file.read_text())
            if data:
                mapping.update({e["name"]: e["ufo_name"] for e in data if "name" in e and "ufo_name" in e})
        return {v: k for k, v in mapping.items()} if reversed else mapping

    monkeypatch.setattr(marty_mod, "_load_ufo_mappings", local_loader, raising=True)

    m = marty_mod.load_ufo_mappings(False)
    assert m["alpha0"] == "aEWM1"
    assert m["Ve1"] == "Ve1"
    assert m["override_me"] == "OVR"

    r = marty_mod.load_ufo_mappings(True)
    assert r["aEWM1"] == "alpha0"
    assert r["Ve1"] == "Ve1"
    assert r["OVR"] == "override_me"
