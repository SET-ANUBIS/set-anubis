import os
from pathlib import Path
import re
from types import SimpleNamespace
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
    monkeypatch.setattr(
        mtm_mod, "decay_name", lambda mother, daug, nsa, mapping: "fake", raising=True
    )
    monkeypatch.setattr(
        mtm_mod,
        "load_particle_mappings",
        lambda *args, **kwargs: {"23": "Z", "2": "u", "11": "e"},
        raising=True,
    )
    monkeypatch.setattr(
        mtm_mod, "load_ufo_mappings", lambda reversed=True, *args, **kwargs: {}, raising=True
    )

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

    mapping_dir = fake_root / "Assets" / "MARTY" / "model"
    mapping_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir = fake_root / "Assets" / "MARTY" / "MartyTemp"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    template_dir = fake_root / "Assets" / "MARTY" / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    paths = SimpleNamespace(
        mapping_dir=mapping_dir,
        model_path=None,
        workspace_dir=workspace_dir,
        template_dir=template_dir,
        marty_install=None,
    )

    return {"root": fake_root, "paths": paths}


def test_analytic_change_model_and_particles_and_paths(patch_mappings_and_names):
    nsa = FakeNSA(masses={})
    mgr = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mothers=MultiSet([23]),
        daugthers=MultiSet([2, -2]),
        template_type=mtm_mod.TemplateType.ANALYTIC,
        nsa=nsa,
        path_config=patch_mappings_and_names["paths"],
    )

    mgr._change_model()
    mgr._change_particles()
    mgr._update_marty_include_path()

    out = mgr._temp

    assert '#include "marty/models/sm.h"' in out
    assert '#include "marty.h"' in out

    assert re.search(r"\bSM_Model\s+model\s*;", out)

    assert 'Incoming("Z")' in out
    assert 'Outgoing("u")' in out
    assert 'Outgoing(AntiPart("u"))' in out

    assert 'system("rm -rf libs/decay_widths_fake");' in out
    assert 'mty::Library decayLib("decay_widths_fake", "libs");' in out


def test_numeric_include_namespace_and_runtime_csv_inputs(patch_mappings_and_names):
    nsa = FakeNSA(masses={23: 91.1876, 11: 0.000511})
    mgr = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mothers=MultiSet([23]),
        daugthers=MultiSet([11, -11]),
        template_type=mtm_mod.TemplateType.NUMERIC,
        nsa=nsa,
        path_config=patch_mappings_and_names["paths"],
    )

    out = mgr.prepare()

    assert '#include "decay_widths_fake.h"' in out
    assert "using namespace decay_widths_fake;" in out
    assert re.search(
        r'std::string ParamFilePath = ".*/Assets/MARTY/MartyTemp/libs/decay_widths_fake/bin/paramlist\.csv";',
        out,
    )
    assert re.search(
        r'std::string PartFilePath = ".*/Assets/MARTY/MartyTemp/libs/decay_widths_fake/bin/partlist\.csv";',
        out,
    )
    assert "auto [outgoing_masses, incoming_masses] = readParts(PartFile);" in out
    assert "Kinematics kin{incoming_masses.at(0), outgoing_masses, &param};" in out
    # Physical masses must not be compiled into the executable.
    assert "91.1876" not in out
    assert "0.000511" not in out


def test_numeric_source_is_independent_of_runtime_masses(patch_mappings_and_names):
    common = dict(
        model_name="SM",
        mothers=MultiSet([23]),
        daugthers=MultiSet([11, -11]),
        template_type=mtm_mod.TemplateType.NUMERIC,
        path_config=patch_mappings_and_names["paths"],
    )
    source_a = mtm_mod.MartyTemplateManager(
        nsa=FakeNSA(masses={23: 91.1876, 11: 0.000511}), **common
    ).prepare()
    source_b = mtm_mod.MartyTemplateManager(
        nsa=FakeNSA(masses={23: 10.0, 11: 0.001}), **common
    ).prepare()
    assert source_a == source_b


def test_public_prepare_and_render_helpers(patch_mappings_and_names):
    nsa = FakeNSA(masses={23: 91.1876, 11: 0.000511})
    analytic = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mothers=MultiSet([23]),
        daugthers=MultiSet([11, -11]),
        template_type=mtm_mod.TemplateType.ANALYTIC,
        nsa=nsa,
        path_config=patch_mappings_and_names["paths"],
    )
    rendered = analytic.prepare()
    assert rendered == analytic.render()
    assert 'Incoming("Z")' in rendered
    assert "decay_widths_fake" in rendered

    numeric = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mothers=MultiSet([23]),
        daugthers=MultiSet([11, -11]),
        template_type=mtm_mod.TemplateType.NUMERIC,
        nsa=nsa,
        path_config=patch_mappings_and_names["paths"],
    )
    numeric_source = numeric.prepare()
    assert '#include "decay_widths_fake.h"' in numeric_source
    assert "paramlist.csv" in numeric_source
    assert "partlist.csv" in numeric_source


def test_explicit_marty_include_directory(
    monkeypatch, patch_mappings_and_names, tmp_path
):
    """Embed a concrete marty.h path only when explicitly configured."""
    include_dir = tmp_path / "marty-include"
    monkeypatch.setenv("SETANUBIS_MARTY_INCLUDE_DIR", str(include_dir))
    mgr = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mothers=MultiSet([23]),
        daugthers=MultiSet([2, -2]),
        template_type=mtm_mod.TemplateType.ANALYTIC,
        nsa=FakeNSA(masses={}),
        path_config=patch_mappings_and_names["paths"],
    )

    source = mgr.prepare()

    assert f'#include "{(include_dir / "marty.h").resolve().as_posix()}"' in source


def test_mediator_components_generate_separate_amplitudes_and_interference(
    patch_mappings_and_names,
):
    from SetAnubis.core.BranchingRatio.domain.MartyAmplitudeConfig import (
        normalize_mediator_fermion_orders,
    )

    components = normalize_mediator_fermion_orders(
        {
            "W": [2, 0, 3, 1],
            "Z": [3, 0, 2, 1],
        }
    )
    mgr = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mothers=MultiSet([23]),
        daugthers=MultiSet([11, -11]),
        template_type=mtm_mod.TemplateType.ANALYTIC,
        nsa=FakeNSA(masses={}),
        path_config=patch_mappings_and_names["paths"],
        amplitude_components=components,
    )

    source = mgr.prepare()

    assert "opts_component_0.setFermionOrder({2, 0, 3, 1});" in source
    assert "opts_component_1.setFermionOrder({3, 0, 2, 1});" in source
    assert 'diag.isMediator("W")' in source
    assert 'diag.isMediator("Z")' in source
    assert "computeSquaredAmplitude(ampli_component_0);" in source
    assert "computeSquaredAmplitude(ampli_component_1);" in source
    assert "computeSquaredAmplitude(ampli_component_0, ampli_component_1);" in source
    assert "computeSquaredAmplitude(ampli_component_1, ampli_component_0);" in source
    assert "auto ampli =" not in source
    assert "__mfo_" in source


def test_default_analytic_path_remains_single_amplitude(patch_mappings_and_names):
    mgr = mtm_mod.MartyTemplateManager(
        model_name="SM",
        mothers=MultiSet([23]),
        daugthers=MultiSet([11, -11]),
        template_type=mtm_mod.TemplateType.ANALYTIC,
        nsa=FakeNSA(masses={}),
        path_config=patch_mappings_and_names["paths"],
    )
    source = mgr.prepare()
    assert "FeynOptions opts;" in source
    assert "auto ampli = model.computeAmplitude" in source
    assert "Expr decay_width = model.computeSquaredAmplitude(ampli);" in source
    assert "opts_component_" not in source
