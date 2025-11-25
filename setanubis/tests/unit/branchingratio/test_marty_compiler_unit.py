from pathlib import Path
import os
import types
import pytest

import SetAnubis.core.BranchingRatio.domain.MartyCompiler as mc_mod


def _patch_module_root(monkeypatch, tmp_path: Path, module):
    """
    Force Path(__file__).resolve() to send a deep path for
    module.Path(__file__).resolve().parents[5] to go to tmp_path/"root".
    """
    root = tmp_path / "root"
    nested = root / "a" / "b" / "c" / "d" / "e" / "module.py"
    nested.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module.Path, "resolve", lambda *_a, **_k: nested, raising=False)
    return root


class StubProc:
    """Stub of subprocess.run which capture calls and send back the call instruction."""
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.calls = []
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __call__(self, command, shell, stdout, stderr, text):
        self.calls.append(command)
        class R:
            pass
        r = R()
        r.returncode = self.returncode
        r.stdout = self.stdout
        r.stderr = self.stderr
        return r


def test_init_requires_ampli_for_make(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    with pytest.raises(ValueError, match="ampli_name needs to be specified"):
        mc_mod.MartyCompiler(mc_mod.CompilerType.MAKE)


def test_check_if_compile_make_true_false(monkeypatch, tmp_path):
    root = _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.MAKE, "decay_widths_fake")

    bin_dir = comp.libs_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    bin_file = bin_dir / "example_decay_widths_fake.x"

    assert comp.check_if_compile(output_binary="ignored") is False

    bin_file.write_text("", encoding="utf-8")
    bin_file.chmod(0o755)
    assert comp.check_if_compile(output_binary="ignored") is True


def test_check_if_compile_gcc_absolute_ok(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)

    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.GCC, "anything")

    abs_bin = tmp_path / "prog.x"
    abs_bin.write_text("", encoding="utf-8")
    abs_bin.chmod(0o755)

    assert comp.check_if_compile(str(abs_bin)) is True


def test_check_if_compile_gcc_bad_extension(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.GCC, "x")

    bad = tmp_path / "prog.exe"
    bad.write_text("", encoding="utf-8")
    bad.chmod(0o755)

    with pytest.raises(ValueError, match="Expected binary path"):
        comp.check_if_compile(str(bad))


def test_compile_gcc_builds_command(monkeypatch, tmp_path):
    root = _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.GCC, "x")

    src = tmp_path / "main.cpp"
    out = tmp_path / "main.x"
    comp.marty_lib_path.mkdir(parents=True, exist_ok=True)
    src.write_text("// stub\n", encoding="utf-8")

    stub = StubProc(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    comp.compile(str(src), str(out))

    assert len(stub.calls) == 1
    cmd = stub.calls[0]
    assert "g++ -o" in cmd
    assert str(src) in cmd and str(out) in cmd

    assert f"-L{comp.marty_lib_path}" in cmd
    assert f"-Wl,-rpath,{comp.marty_lib_path}" in cmd
    assert "-lmarty" in cmd and "-lgfortran" in cmd


def test_compile_make_builds_command(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.MAKE, "decay_widths_fake")
    comp.libs_path.mkdir(parents=True, exist_ok=True)

    stub = StubProc(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    comp.compile(source_file="ignored", output_binary="ignored")

    assert len(stub.calls) == 1
    cmd = stub.calls[0]
    assert cmd == f"cd {comp.libs_path} && make"


def test_compile_run_gcc_triggers_compile_then_run_with_pattern(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.GCC, "A")

    src = tmp_path / "calc.cpp"
    src.write_text("//...\n", encoding="utf-8")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    out_bin = out_dir / "calc.x"

    stub = StubProc(returncode=0, stdout="... Value : 123.4 ...", stderr="")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    val = comp.compile_run(source_file=str(src), output_binary=str(out_bin), output_dir=str(out_dir), pattern=r"Value\s*:\s*([0-9\.]+)")

    assert len(stub.calls) == 2
    assert "g++ -o" in stub.calls[0]
    assert stub.calls[1].startswith(f"cd {out_dir} && ./calc.x")
    assert val == "123.4"


def test_execute_command_error_raises(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.MAKE, "fake")
    comp.libs_path.mkdir(parents=True, exist_ok=True)

    stub = StubProc(returncode=2, stdout="", stderr="boom")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    with pytest.raises(RuntimeError, match="Command failed"):
        comp.execute_command("echo test")


def test_execute_command_gcc_skips_when_already_executed(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)

    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.GCC, "decay_widths_foo")

    script = comp.libs_path / "script"
    script.mkdir(parents=True, exist_ok=True)
    (script / f"example_{comp.ampli_name}.cpp").write_text("// already\n", encoding="utf-8")

    out_dir = tmp_path / "bld"; out_dir.mkdir()
    out_bin = out_dir / "prog.x"; out_bin.write_text("", encoding="utf-8"); out_bin.chmod(0o755)

    stub = StubProc(returncode=0, stdout="IGNORED", stderr="")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    res = comp.compile_run(source_file="ignored.cpp", output_binary=str(out_bin), output_dir=str(out_dir))
    
    assert res is None
    assert len(stub.calls) == 0
