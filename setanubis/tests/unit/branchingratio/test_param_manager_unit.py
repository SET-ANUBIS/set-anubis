import math
from pathlib import Path
import pytest

import SetAnubis.core.BranchingRatio.domain.MartyParamManager as pm_mod


class FakeNSA:
    """Provide get_parameter_value(name) returning a complex value."""
    def __init__(self, values):
        self.values = {k: complex(v, 0.0) for k, v in values.items()}
    def get_parameter_value(self, name: str):
        return self.values[name]


@pytest.fixture
def header_file(tmp_path: Path) -> Path:
    #   csl::InitSanitizer<real_t>    NAME {
    #   csl::InitSanitizer<complex_t> NAME {
    text = """
// Some header...
csl::InitSanitizer<real_t> alpha0 {
    // ...
};
csl::InitSanitizer<complex_t> Ve1 {
    // ...
};
csl::InitSanitizer<real_t> s_12 { };     // excluded
csl::InitSanitizer<real_t> reg_prop { }; // special
csl::InitSanitizer<real_t> theta_W { };  // special, depends on sw
"""
    p = tmp_path / "params.h"
    p.write_text(text, encoding="utf-8")
    return p


def test_param_manager_parses_and_fetches_values(header_file, monkeypatch):
    def fake_load_ufo_mappings(reversed: bool = False):
        return {"alpha0": "aEWM1"}
    monkeypatch.setattr(pm_mod, "load_ufo_mappings", fake_load_ufo_mappings, raising=True)

    nsa = FakeNSA({
        "aEWM1": 127.9,
        "Ve1": 0.0,
        "sw": 0.48,
    })

    mgr = pm_mod.ParamManager(header_path=header_file, nsa=nsa)
    params = mgr.get_parameters()

    names = {p.name for p in params}
    assert "alpha0" in names
    assert "Ve1" in names
    assert "reg_prop" in names
    assert "theta_W" in names
    assert "s_12" not in names

    tmap = {p.name: p.type for p in params}
    assert tmap["alpha0"] == pm_mod.ParameterType.REAL
    assert tmap["Ve1"] == pm_mod.ParameterType.COMPLEX

    umap = {p.name: p.ufo_name for p in params}
    assert umap["alpha0"] == "aEWM1"
    assert umap["Ve1"] == "Ve1"


    dvals = {p.name: p.value for p in params}
    assert dvals["alpha0"] == pytest.approx(127.9, rel=1e-12)
    assert dvals["reg_prop"] == pytest.approx(1e-5, rel=1e-12)
    assert dvals["theta_W"] == pytest.approx(math.asin(0.48), rel=1e-12)

    d = mgr.as_dict()
    assert d["alpha0"]["type"] == "real_t"
    assert d["alpha0"]["ufo_name"] == "aEWM1"
    assert d["alpha0"]["value"] == pytest.approx(127.9)

    csv = mgr.create_csv()
    assert "alpha0,127.9" in csv
    assert "reg_prop,1e-05" in csv


def test_particle_csv_and_finite_special_value(header_file, monkeypatch):
    """Serialize process particles and resolve the generated Finite constant."""
    monkeypatch.setattr(pm_mod, "load_ufo_mappings", lambda reversed=False: {})
    monkeypatch.setattr(pm_mod, "load_particle_mappings", lambda reversed=False: {})

    class ParticleNSA(FakeNSA):
        def get_particle_info(self, pdg):
            return {"name": {23: "Z", 5: "b", -5: "b~"}[pdg]}

        def get_particle_mass(self, pdg):
            return {23: 91.2, 5: 4.2, -5: 4.2}[pdg]

    finite_header = header_file.parent / "finite.h"
    finite_header.write_text(
        "csl::InitSanitizer<real_t> Finite { };\n", encoding="utf-8"
    )
    manager = pm_mod.ParamManager(finite_header, ParticleNSA({}))
    assert manager.get_parameters()[0].value == 1.0 + 0j
    assert manager.create_particle_csv([23], [5, -5]) == (
        "Z_in,91.2\nb_out,4.2\nb~_out,4.2\n"
    )
