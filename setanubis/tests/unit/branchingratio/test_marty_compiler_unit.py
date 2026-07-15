from pathlib import Path

import pytest

import SetAnubis.core.BranchingRatio.domain.MartyCompiler as mc_mod


def _patch_module_root(monkeypatch, tmp_path: Path, module):
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

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))

        class Result:
            pass

        result = Result()
        result.returncode = self.returncode
        result.stdout = self.stdout
        result.stderr = self.stderr
        return result


def test_init_requires_ampli_for_make(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    with pytest.raises(ValueError, match="ampli_name needs to be specified"):
        mc_mod.MartyCompiler(mc_mod.CompilerType.MAKE)


def test_check_if_compile_make_true_false(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
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


def test_compile_gcc_builds_argument_list(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.GCC, "x")

    src = tmp_path / "source with spaces.cpp"
    out = tmp_path / "output with spaces.x"
    comp.marty_lib_path.mkdir(parents=True, exist_ok=True)
    src.write_text("// stub\n", encoding="utf-8")

    stub = StubProc()
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    comp.compile(str(src), str(out))

    assert len(stub.calls) == 1
    command, kwargs = stub.calls[0]
    assert command[:4] == ["g++", "-o", str(out.absolute()), str(src.absolute())]
    assert f"-L{comp.marty_lib_path}" in command
    assert f"-Wl,-rpath,{comp.marty_lib_path}" in command
    assert "-lmarty" in command and "-lgfortran" in command
    assert kwargs["cwd"] is None
    assert kwargs["check"] is False
    assert "shell" not in kwargs


def test_compile_make_uses_cwd_without_shell(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.MAKE, "decay_widths_fake")
    comp.libs_path.mkdir(parents=True, exist_ok=True)

    stub = StubProc()
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    comp.compile(source_file="ignored", output_binary="ignored")

    command, kwargs = stub.calls[0]
    assert command == ["make"]
    assert kwargs["cwd"] == str(comp.libs_path)
    assert "shell" not in kwargs


def test_compile_run_gcc_triggers_compile_then_run_with_pattern(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.GCC, "A")

    src = tmp_path / "calc.cpp"
    src.write_text("//...\n", encoding="utf-8")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    out_bin = out_dir / "calc.x"

    stub = StubProc(stdout="... Value : 123.4 ...")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    value = comp.compile_run(
        source_file=str(src),
        output_binary=str(out_bin),
        output_dir=str(out_dir),
        pattern=r"Value\s*:\s*([0-9\.]+)",
    )

    assert len(stub.calls) == 2
    compile_command, _ = stub.calls[0]
    run_command, run_kwargs = stub.calls[1]
    assert compile_command[0] == "g++"
    assert run_command == [str(out_bin.absolute())]
    assert run_kwargs["cwd"] == str(out_dir.absolute())
    assert value == "123.4"


def test_execute_command_error_raises(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.MAKE, "fake")
    comp.libs_path.mkdir(parents=True, exist_ok=True)

    stub = StubProc(returncode=2, stderr="boom")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    with pytest.raises(RuntimeError, match="Command failed"):
        comp.execute_command(["echo", "test"])


def test_execute_command_rejects_shell_string(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.MAKE, "fake")
    with pytest.raises(TypeError, match="sequence of arguments"):
        comp.execute_command("echo test")


def test_execute_command_gcc_skips_when_already_executed(monkeypatch, tmp_path):
    _patch_module_root(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(mc_mod.CompilerType.GCC, "decay_widths_foo")

    script = comp.libs_path / "script"
    script.mkdir(parents=True, exist_ok=True)
    (script / f"example_{comp.ampli_name}.cpp").write_text("// already\n", encoding="utf-8")

    out_dir = tmp_path / "bld"
    out_dir.mkdir()
    out_bin = out_dir / "prog.x"
    out_bin.write_text("", encoding="utf-8")
    out_bin.chmod(0o755)

    stub = StubProc(stdout="IGNORED")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    result = comp.compile_run(
        source_file="ignored.cpp",
        output_binary=str(out_bin),
        output_dir=str(out_dir),
    )

    assert result is None
    assert len(stub.calls) == 0
