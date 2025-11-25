from pathlib import Path
import os
import pytest

import SetAnubis.core.BranchingRatio.domain.MartyManager as mm_mod
from SetAnubis.core.Common.MultiSet import MultiSet


def _patch_root(monkeypatch, tmp_path: Path, module):
    root = tmp_path / "root"
    nested = root / "a" / "b" / "c" / "d" / "e" / "module.py"
    nested.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module.Path, "resolve", lambda *_a, **_k: nested, raising=False)
    return root


class WritingCopyManager:
    instances = []
    def __init__(self, ampli_name, builder):
        self.ampli_name = ampli_name
        self.builder = builder
        self.executed = False
        WritingCopyManager.instances.append(self)

    def write_file(self, code, path, force=False):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(code))
        return path

    def execute(self):
        self.executed = True


class StubTemplateManager:
    def __init__(self, model_name, mother, daughters, template_type, nsa):
        self._temp = f"{template_type.value}_CODE"
    def _change_model(self): pass
    def _change_particles(self): pass
    def _update_marty_include_path(self): pass
    def _change_paramlist(self): pass


class StubParamManager:
    def __init__(self, header_path, nsa):
        self.header_path = Path(header_path)
        self.nsa = nsa
    def create_csv(self):
        return "p,3\nq,4\n"
    def create_particle_csv(self, mothers, daugthers):
        return "23_in,91\n2_out,0.006\n-2_out,0,006\n"


class StubCompiler:
    calls = []
    def __init__(self, compiler_type, ampli_name=None):
        self.compiler_type = compiler_type
        self.ampli = ampli_name
        root = mm_mod.Path(mm_mod.__file__).resolve().parents[5]
        self.libs_path = root / "Assets" / "MARTY" / "MartyTemp" / "libs" / (ampli_name or "none")

    def compile_run(self, source_file, output_binary=None, output_dir=None, pattern=None):
        StubCompiler.calls.append(
            (self.compiler_type, self.ampli,
             str(source_file),
             None if output_binary is None else str(output_binary),
             None if output_dir is None else str(output_dir),
             pattern)
        )
        if pattern:
            return "7.77"
        return None



@pytest.fixture(autouse=True)
def patch_all(monkeypatch, tmp_path):
    _ = _patch_root(monkeypatch, tmp_path, mm_mod)
    monkeypatch.setattr(mm_mod, "decay_name",
                        lambda mother, dau, neo, mapping: "fake",
                        raising=True)
    monkeypatch.setattr(mm_mod, "load_ufo_mappings",
                        lambda reversed=True: {},
                        raising=True)
    monkeypatch.setattr(mm_mod, "CopyManager", WritingCopyManager, raising=True)
    monkeypatch.setattr(mm_mod, "MartyTemplateManager", StubTemplateManager, raising=True)
    monkeypatch.setattr(mm_mod, "ParamManager", StubParamManager, raising=True)
    monkeypatch.setattr(mm_mod, "MartyCompiler", StubCompiler, raising=True)


def test_end_to_end_builds_files_and_calls_compilers(tmp_path):
    mgr = mm_mod.MartyManager("SM")
    nsa = object()

    mgr.build_analytic(23, MultiSet([2, -2]), nsa, builder_marty=object())
    analytic_cpp = tmp_path / "root" / "Assets" / "MARTY" / "MartyTemp" / "fake.cpp"
    assert analytic_cpp.exists()
    assert analytic_cpp.read_text() == "ANALYTIC_CODE"

    mm_mod.neo = nsa
    mgr.launch_analytic(23, MultiSet([2, -2]))
    assert StubCompiler.calls and StubCompiler.calls[-1][0] == mm_mod.CompilerType.GCC

    mgr.build_numeric(23, MultiSet([2, -2]), nsa, builder_marty=object())
    script_cpp = tmp_path / "root" / "Assets" / "MARTY" / "MartyTemp" / "libs" / "decay_widths_fake" / "script" / "example_decay_widths_fake.cpp"
    csv_file = tmp_path / "root" / "Assets" / "MARTY" / "MartyTemp" / "libs" / "decay_widths_fake" / "bin" / "paramlist.csv"
    assert script_cpp.exists() and csv_file.exists()
    assert "NUMERIC_CODE" in script_cpp.read_text()
    assert "p,3" in csv_file.read_text()

    val = mgr.launch_numeric(23, MultiSet([2, -2]), nsa)
    assert val == pytest.approx(7.77)
