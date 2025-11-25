import os
import re
from pathlib import Path
import pytest

from SetAnubis.core.Common.MultiSet import MultiSet
import SetAnubis.core.BranchingRatio.domain.MartyTemplateManager as mtm_mod


class FakeNSA:
    def __init__(self, masses):
        self._m = dict(masses)
    def get_particle_mass(self, pdg: int) -> float:
        return float(self._m.get(abs(pdg), 0.0))


@pytest.fixture(autouse=True)
def patch_all(monkeypatch, tmp_path):
    monkeypatch.setattr(mtm_mod, "decay_name",
                        lambda mother, daug, nsa, mapping: "fake",
                        raising=True)
    monkeypatch.setattr(mtm_mod, "load_particle_mappings",
                        lambda: {"24": "W", "11": "e", "12": "nu_e", "23": "Z"},
                        raising=True)
    monkeypatch.setattr(mtm_mod, "load_ufo_mappings",
                        lambda reversed=True: {},
                        raising=True)
    real_abspath = os.path.abspath
    module_file = mtm_mod.__file__
    fake_root = tmp_path
    nested = fake_root / "a" / "b" / "c" / "d" / "e" / "f" / "module.cpp"
    nested.parent.mkdir(parents=True, exist_ok=True)
    def fake_abspath(p):
        if p == module_file:
            return str(nested)
        return real_abspath(p)
    monkeypatch.setattr(mtm_mod.os.path, "abspath", fake_abspath, raising=True)

    return {"root": fake_root}


def test_end_to_end_strings_for_analytic_and_numeric():
    nsa = FakeNSA(masses={})
    ana = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mothers=[23],
        daugthers=MultiSet([11, -11]),
        template_type=mtm_mod.TemplateType.ANALYTIC,
        nsa=nsa,
    )
    ana._change_model()
    ana._change_particles()
    ana._update_marty_include_path()
    txt_a = ana._temp

    assert 'SM_Model model;' in txt_a
    assert 'Incoming("Z")' in txt_a
    assert 'Outgoing("e")' in txt_a and 'Outgoing(AntiPart("e"))' in txt_a
    assert 'decay_widths_fake' in txt_a

    nsa2 = FakeNSA(masses={24: 80.379, 11: 0.000511, 12: 0.0})
    num = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mothers=[-24, 24],
        daugthers=MultiSet([11, 12]),
        template_type=mtm_mod.TemplateType.NUMERIC,
        nsa=nsa2,
    )
    num._change_paramlist()
    num._change_particles()
    txt_n = num._temp

    assert '#include "decay_widths_fake.h"' in txt_n
    assert 'using namespace decay_widths_fake;' in txt_n
    assert "{{80.379, 80.379}, {0.000511, 0.0}," in txt_n
