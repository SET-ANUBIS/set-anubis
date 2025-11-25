from pathlib import Path
import pytest

import SetAnubis.core.BranchingRatio.domain.MartyManager as mm_mod
from SetAnubis.core.Common.MultiSet import MultiSet


def _patch_root(monkeypatch, tmp_path: Path, module):
    """
    Force Path(__file__).resolve() à renvoyer .../root/a/b/c/d/e/module.py,
    ainsi module.Path(__file__).resolve().parents[5] == tmp_path/'root'.
    """
    root = tmp_path / "root"
    nested = root / "a" / "b" / "c" / "d" / "e" / "module.py"
    nested.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module.Path, "resolve", lambda *_a, **_k: nested, raising=False)
    return root


class FakeNSA:
    pass


class FakeTemplateManager:
    def __init__(self, model_name, mother, daughters, template_type, nsa):
        self.model_name = model_name
        self.mother = mother
        self.daughters = daughters
        self.template_type = template_type
        self.nsa = nsa
        self._temp = f"{template_type.value}_TEMPLATE"

    def _change_model(self): self._temp += "|MODEL"
    def _change_particles(self): self._temp += "|PARTICLES"
    def _update_marty_include_path(self): self._temp += "|MARTY_PATH"
    def _change_paramlist(self): self._temp += "|PARAMLIST"


class FakeCopyManager:
    instances = []
    def __init__(self, ampli_name, builder):
        self.ampli_name = ampli_name
        self.builder = builder
        self.writes = []
        self.executed = False
        FakeCopyManager.instances.append(self)

    def write_file(self, code, path, force=False):
        self.writes.append((str(code), Path(path), bool(force)))
        return Path(path)

    def execute(self):
        self.executed = True


class FakeCompiler:
    last_calls = []
    def __init__(self, compiler_type, ampli_name=None):
        self.compiler_type = compiler_type
        self.ampli_name = ampli_name
        root = mm_mod.Path(mm_mod.__file__).resolve().parents[5]
        self.libs_path = root / "Assets" / "MARTY" / "MartyTemp" / "libs" / (ampli_name or "none")

    def compile_run(self, source_file, output_binary=None, output_dir=None, pattern=None):
        FakeCompiler.last_calls.append(
            ("compile_run", self.compiler_type, self.ampli_name,
             str(source_file),
             None if output_binary is None else str(output_binary),
             None if output_dir is None else str(output_dir),
             pattern)
        )
        if pattern:
            return "12.34"
        return None


class FakeParamManager:
    def __init__(self, header_path, nsa):
        self.header_path = Path(header_path)
        self.nsa = nsa
    def create_csv(self):
        return "a,1\nb,2\n"


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch, tmp_path):
    _ = _patch_root(monkeypatch, tmp_path, mm_mod)
    
    monkeypatch.setattr(mm_mod, "decay_name",
                        lambda mother, daughters, neo, mapping: "fake",
                        raising=True)
    monkeypatch.setattr(mm_mod, "load_ufo_mappings",
                        lambda reversed=True: {},
                        raising=True)

    monkeypatch.setattr(mm_mod, "MartyTemplateManager", FakeTemplateManager, raising=True)
    monkeypatch.setattr(mm_mod, "CopyManager", FakeCopyManager, raising=True)
    monkeypatch.setattr(mm_mod, "MartyCompiler", FakeCompiler, raising=True)
    monkeypatch.setattr(mm_mod, "ParamManager", FakeParamManager, raising=True)



def test_build_analytic_writes_cpp(tmp_path):
    mgr = mm_mod.MartyManager("SM")
    nsa = FakeNSA()
    builder = object() 

    mgr.build_analytic(23, MultiSet([2, -2]), nsa, builder)

    assert FakeCopyManager.instances, "CopyManager non instancié"
    cm = FakeCopyManager.instances[-1]
    assert cm.ampli_name == "decay_widths_fake"

    assert len(cm.writes) == 1
    code, path, force = cm.writes[0]
    assert path.as_posix().endswith("Assets/MARTY/MartyTemp/fake.cpp")
    assert "ANALYTIC_TEMPLATE|MODEL|PARTICLES|MARTY_PATH" in code
    assert force is False


def test_launch_analytic_calls_compiler_and_paths(monkeypatch, tmp_path):
    mm_mod.neo = FakeNSA()

    mgr = mm_mod.MartyManager("SM")
    mgr.launch_analytic(23, MultiSet([2, -2]))

    assert FakeCompiler.last_calls, "compile_run non appelé"
    tag, ctype, ampli, src, out, outdir, pattern = FakeCompiler.last_calls[-1]
    assert tag == "compile_run"
    assert ctype == mm_mod.CompilerType.GCC
    assert ampli == "decay_widths_fake"
    assert src.endswith("Assets/MARTY/MartyTemp/fake.cpp")
    assert out.endswith("Assets/MARTY/MartyTemp/fake")
    assert outdir.endswith("Assets/MARTY/MartyTemp")
    assert pattern is None


def test_build_numeric_exec_copy_and_write_csv(tmp_path):
    FakeCopyManager.instances.clear()

    mgr = mm_mod.MartyManager("SM")
    nsa = FakeNSA()
    builder = object()

    mgr.build_numeric(23, MultiSet([2, -2]), nsa, builder)

    cm = FakeCopyManager.instances[-1]

    assert cm.executed is True

    paths = [p.as_posix() for (_, p, _) in cm.writes]
    found_script = any(p.endswith("Assets/MARTY/MartyTemp/libs/decay_widths_fake/script/example_decay_widths_fake.cpp") for p in paths)
    found_csv = any(p.endswith("Assets/MARTY/MartyTemp/libs/decay_widths_fake/bin/paramlist.csv") for p in paths)
    assert found_script and found_csv


def test_launch_numeric_returns_float(monkeypatch, tmp_path):
    mgr = mm_mod.MartyManager("SM")
    nsa = FakeNSA()

    val = mgr.launch_numeric(23, MultiSet([2, -2]), nsa)
    assert isinstance(val, float) and val == pytest.approx(12.34)


def test_calculate_process_orchestrates(monkeypatch):
    calls = []
    mgr = mm_mod.MartyManager("SM")
    monkeypatch.setattr(mgr, "build_analytic", lambda *a, **k: calls.append("build_analytic"))
    monkeypatch.setattr(mgr, "launch_analytic", lambda *a, **k: calls.append("launch_analytic"))
    monkeypatch.setattr(mgr, "build_numeric", lambda *a, **k: calls.append("build_numeric"))
    monkeypatch.setattr(mgr, "launch_numeric", lambda *a, **k: (calls.append("launch_numeric"), 42.0)[1])

    res = mgr.calculate_process(23, MultiSet([2, -2]), FakeNSA(), object())
    assert calls == ["build_analytic", "launch_analytic", "build_numeric", "launch_numeric"]
    assert res == 42.0
