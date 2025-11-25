import os
from pathlib import Path
import re
import pytest

from SetAnubis.core.Common.MultiSet import MultiSet
import SetAnubis.core.BranchingRatio.domain.MartyTemplateManager as mtm_mod


class FakeNSA:
    def __init__(self, masses):
        self._m = dict(masses)
    def get_particle_mass(self, pdg: int) -> float:
        return float(self._m.get(abs(pdg), 0.0))


@pytest.fixture
def patch_mappings_and_names(monkeypatch, tmp_path):
    monkeypatch.setattr(mtm_mod, "decay_name",
                        lambda mother, daug, nsa, mapping: "fake",
                        raising=True)
    monkeypatch.setattr(mtm_mod, "load_particle_mappings",
                        lambda: {"23": "Z", "2": "u", "11": "e"},
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


def test_analytic_change_model_and_particles_and_paths(patch_mappings_and_names):
    nsa = FakeNSA(masses={})
    mgr = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mother=23,
        daugthers=MultiSet([2, -2]),
        template_type=mtm_mod.TemplateType.ANALYTIC,
        nsa=nsa,
    )

    mgr._change_model()
    mgr._change_particles()
    mgr._update_marty_include_path()

    out = mgr._temp

    assert re.search(r'#include\s+".*/Assets/MARTY/model/sm\.h"', out)

    assert re.search(r'\bSM_Model\s+model\s*;', out)

    assert 'Incoming("Z")' in out
    assert 'Outgoing("u")' in out
    assert 'Outgoing(AntiPart("u"))' in out

    assert 'system("rm -rf libs/decay_widths_fake");' in out
    assert 'mty::Library decayLib("decay_widths_fake", "libs");' in out


def test_numeric_include_namespace_paramlist_and_masses(patch_mappings_and_names):
    nsa = FakeNSA(masses={23: 91.1876, 11: 0.000511})
    mgr = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mother=23,
        daugthers=MultiSet([11, -11]),
        template_type=mtm_mod.TemplateType.NUMERIC,
        nsa=nsa,
    )

    mgr._change_paramlist()
    mgr._change_particles()

    out = mgr._temp

    assert '#include "decay_widths_fake.h"' in out
    assert 'using namespace decay_widths_fake;' in out
    assert re.search(r'std::string ParamFilePath = ".*/Assets/MARTY/MartyTemp/libs/decay_widths_fake/bin/paramlist\.csv";', out)
    assert "{{91.1876}, {0.000511, 0.000511}," in out
