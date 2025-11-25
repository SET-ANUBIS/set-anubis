from pathlib import Path
import os
import pytest

import SetAnubis.core.BranchingRatio.domain.MartyCompiler as mc_mod


def _patch_root_for_module(monkeypatch, tmp_path: Path, module):
    root = tmp_path / "root"
    nested = root / "a" / "b" / "c" / "d" / "e" / "module.py"
    nested.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module.Path, "resolve", lambda *_a, **_k: nested, raising=False)
    return root


class StubProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.calls = []
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
    def __call__(self, command, shell, stdout, stderr, text):
        self.calls.append(command)
        class R: pass
        r = R(); r.returncode=self.returncode; r.stdout=self.stdout; r.stderr=self.stderr
        return r


def test_make_flow_with_existing_binary(monkeypatch, tmp_path):
    root = _patch_root_for_module(monkeypatch, tmp_path, mc_mod)

    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.MAKE, "decay_widths_Z_ee")

    bin_dir = comp.libs_path / "bin"; bin_dir.mkdir(parents=True, exist_ok=True)
    exe = bin_dir / f"example_{comp.ampli_name}.x"
    exe.write_text("", encoding="utf-8"); exe.chmod(0o755)

    stub = StubProc(returncode=0, stdout="run ok", stderr="")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    res = comp.compile_run(source_file="ignored.cpp", output_binary="ignored")

    assert len(stub.calls) == 1
    assert stub.calls[0].startswith(f"cd {comp.libs_path} && ./bin/example_{comp.ampli_name}.x")
    assert res is None


def test_gcc_flow_compile_then_run(monkeypatch, tmp_path):
    root = _patch_root_for_module(monkeypatch, tmp_path, mc_mod)

    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.GCC, "decay_widths_W_en")
    comp.marty_lib_path.mkdir(parents=True, exist_ok=True)

    src = tmp_path / "calc.cpp"; src.write_text("//...", encoding="utf-8")
    out_dir = tmp_path / "out"; out_dir.mkdir()
    out_bin = out_dir / "calc.x" 

    stub = StubProc(returncode=0, stdout="Value : 9.81", stderr="")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    res = comp.compile_run(str(src), str(out_bin), str(out_dir), pattern=r"Value\s*:\s*([0-9\.]+)")

    assert len(stub.calls) == 2
    assert "g++ -o" in stub.calls[0]
    assert stub.calls[1].startswith(f"cd {out_dir} && ./calc.x")
    assert res == "9.81"
