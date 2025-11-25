import math
from pathlib import Path
import json
import yaml
import pytest

import SetAnubis.core.BranchingRatio.domain.MartyParamManager as pm_mod
import SetAnubis.core.BranchingRatio.domain.MartyUtil as marty_mod


class FakeNSA:
    def __init__(self, values):
        self.values = {k: complex(v, 0.0) for k, v in values.items()}
    def get_parameter_value(self, name: str):
        return self.values[name]


def test_param_manager_with_real_mappings(tmp_path: Path, monkeypatch):
    assets = tmp_path / "Assets" / "MARTY" / "model"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "conversion_sm.json").write_text(
        json.dumps([{"name": "alpha0", "ufo_name": "aEWM1"}]), encoding="utf-8")
    (assets / "conversion_model.yaml").write_text(
        yaml.safe_dump([{"name": "Ve1", "ufo_name": "Ve1"}]), encoding="utf-8")

    def local_loader(reversed: bool):
        mapping = {}
        jf = assets / "conversion_sm.json"
        yf = assets / "conversion_model.yaml"
        if jf.exists():
            mapping.update({e["name"]: e["ufo_name"] for e in json.loads(jf.read_text())})
        if yf.exists():
            data = yaml.safe_load(yf.read_text()); 
            if data:
                mapping.update({e["name"]: e["ufo_name"] for e in data})
        return {v: k for k, v in mapping.items()} if reversed else mapping

    monkeypatch.setattr(marty_mod, "_load_ufo_mappings", local_loader, raising=True)
    # NOTE: pm_mod.ParamManager import load_ufo_mappings to module, no need to reload if going through public API
    monkeypatch.setattr(pm_mod, "load_ufo_mappings", marty_mod.load_ufo_mappings, raising=True)

    header = tmp_path / "params.h"
    header.write_text("""
csl::InitSanitizer<real_t> alpha0 { };
csl::InitSanitizer<complex_t> Ve1 { };
csl::InitSanitizer<real_t> theta_W { };
""", encoding="utf-8")

    nsa = FakeNSA({"aEWM1": 127.9, "Ve1": 0.0, "sw": 0.5})

    mgr = pm_mod.ParamManager(header_path=header, nsa=nsa)
    d = mgr.as_dict()

    assert d["alpha0"]["ufo_name"] == "aEWM1"
    assert d["alpha0"]["value"] == pytest.approx(127.9)
    assert d["Ve1"]["ufo_name"] == "Ve1"
    assert d["theta_W"]["value"] == pytest.approx(math.asin(0.5), rel=1e-12)
