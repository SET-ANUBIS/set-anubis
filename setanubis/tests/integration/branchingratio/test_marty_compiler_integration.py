from pathlib import Path
from types import SimpleNamespace

import SetAnubis.core.BranchingRatio.domain.MartyCompiler as mc_mod


def _patch_root_for_module(monkeypatch, tmp_path: Path, module):
    root = tmp_path / "root"
    nested = root / "a" / "b" / "c" / "d" / "e" / "module.py"
    nested.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module.Path, "resolve", lambda *_a, **_k: nested, raising=False)
    return root


def _path_config(root: Path, *, with_install: bool = False):
    workspace = root / "Assets" / "MARTY" / "MartyTemp"
    workspace.mkdir(parents=True, exist_ok=True)
    install = None
    if with_install:
        include_dir = root / "marty" / "include"
        lib_dir = root / "marty" / "lib"
        include_dir.mkdir(parents=True, exist_ok=True)
        lib_dir.mkdir(parents=True, exist_ok=True)
        install = SimpleNamespace(include_dir=include_dir, lib_dir=lib_dir)
    return SimpleNamespace(workspace_dir=workspace, marty_install=install)


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


def test_make_flow_with_existing_binary(monkeypatch, tmp_path):
    root = _patch_root_for_module(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(
        mc_mod.CompilerType.MAKE,
        "decay_widths_Z_ee",
        path_config=_path_config(root),
    )

    bin_dir = comp.libs_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    executable = bin_dir / f"example_{comp.ampli_name}.x"
    executable.write_text("", encoding="utf-8")
    executable.chmod(0o755)

    stub = StubProc(stdout="run ok")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    result = comp.compile_run(source_file="ignored.cpp", output_binary="ignored")

    assert len(stub.calls) == 1
    command, kwargs = stub.calls[0]
    assert command == [str(executable.absolute())]
    assert kwargs["cwd"] == str(comp.libs_path)
    assert result is None


def test_gcc_flow_compile_then_run(monkeypatch, tmp_path):
    root = _patch_root_for_module(monkeypatch, tmp_path, mc_mod)
    comp = mc_mod.MartyCompiler(
        mc_mod.CompilerType.GCC,
        "decay_widths_W_en",
        path_config=_path_config(root, with_install=True),
    )
    comp.marty_lib_path.mkdir(parents=True, exist_ok=True)

    source = tmp_path / "calc.cpp"
    source.write_text("//...", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    output_binary = output_dir / "calc.x"

    stub = StubProc(stdout="Value : 9.81")
    monkeypatch.setattr(mc_mod.subprocess, "run", stub, raising=True)

    result = comp.compile_run(
        str(source),
        str(output_binary),
        str(output_dir),
        pattern=r"Value\s*:\s*([0-9\.]+)",
    )

    assert len(stub.calls) == 2
    assert stub.calls[0][0][0] == "g++"
    assert stub.calls[1][0] == [str(output_binary.absolute())]
    assert stub.calls[1][1]["cwd"] == str(output_dir.absolute())
    assert result == "9.81"
