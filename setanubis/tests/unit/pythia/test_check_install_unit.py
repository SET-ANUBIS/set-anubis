"""Unit tests for the optional Pythia runtime diagnostic command."""

from __future__ import annotations

import json
from types import SimpleNamespace

import SetAnubis.core.Pythia.tools.check_install as check_install
from SetAnubis.core.Pythia.domain.PythiaRunManager import PythiaBindingError


def test_small_diagnostic_helpers(monkeypatch, tmp_path):
    monkeypatch.setattr(check_install.subprocess, "check_output", lambda *a, **k: " /opt/tool \n")
    assert check_install._run(["tool"]) == "/opt/tool"
    monkeypatch.setattr(
        check_install.subprocess,
        "check_output",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("missing")),
    )
    assert check_install._run(["missing"]) is None

    monkeypatch.setenv("SETANUBIS_PYTHIA8_DIR", str(tmp_path))
    assert check_install._path_from_env("SETANUBIS_PYTHIA8_DIR") == str(tmp_path)
    assert check_install._path_from_env("UNSET_SETANUBIS_PATH") is None
    assert check_install._exists(str(tmp_path))
    assert not check_install._exists(None)


def test_binding_build_info_available_and_missing(monkeypatch):
    monkeypatch.setattr(
        check_install,
        "_load_pythia_sim",
        lambda: SimpleNamespace(get_build_info=lambda: {"pythia": "8.3"}),
    )
    assert check_install._binding_build_info() == {"pythia": "8.3"}

    monkeypatch.setattr(
        check_install,
        "_load_pythia_sim",
        lambda: (_ for _ in ()).throw(PythiaBindingError("missing")),
    )
    assert check_install._binding_build_info() is None


def test_collect_print_and_main(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(check_install.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(check_install, "_run", lambda command: f"/opt/{command[0]}")
    monkeypatch.setattr(
        check_install,
        "check_pythia_binding",
        lambda: {"available": True, "module": "pythia_sim", "path": "/tmp/pythia_sim.so", "error": None},
    )
    monkeypatch.setattr(check_install, "_binding_build_info", lambda: {"compiler": "gcc"})
    monkeypatch.setattr(check_install.ctypes.util, "find_library", lambda name: f"lib{name}.so")
    monkeypatch.setattr(
        check_install.importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(name=name),
    )
    monkeypatch.setattr(check_install, "_exists", lambda path: True)

    report = check_install.collect_diagnostics()
    assert report["python_binding"]["available"] is True
    assert report["tools"]["pythia8-config"] == "/usr/bin/pythia8-config"
    assert report["python_modules"] == {"pybind11": True, "pyhepmc": True}

    check_install.print_human(report)
    assert "Pythia Python binding: OK" in capsys.readouterr().out

    monkeypatch.setattr(check_install, "collect_diagnostics", lambda: report)
    banner_calls = []
    monkeypatch.setattr(
        check_install,
        "show_banner",
        lambda **kwargs: banner_calls.append(kwargs) or True,
    )

    assert check_install.main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out)["python_binding"]["available"] is True
    assert banner_calls == []

    missing = dict(report)
    missing["python_binding"] = {"available": False, "module": None, "path": None, "error": "not built"}
    missing["binding_build_info"] = None
    monkeypatch.setattr(check_install, "collect_diagnostics", lambda: missing)
    assert check_install.main([]) == 1
    output = capsys.readouterr().out
    assert "Pythia Python binding: MISSING" in output
    assert "not built" in output
    assert banner_calls == [{"force": True}]
