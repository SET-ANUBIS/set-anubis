from pathlib import Path
import os
import pytest

import SetAnubis.core.BranchingRatio.domain.MartyCopyManager as cm_mod


class FakeBuilder:
    def __init__(self):
        self.calls = []
    def add_file(self, src, dest, modifications):
        self.calls.append((Path(src), Path(dest), list(modifications)))
    def execute(self):
        pass


def _patch_module_root_to_tmp(monkeypatch, tmp_path: Path, module):
    """Force Path(__file__).resolve() à renvoyer un chemin profond dans tmp_path."""
    nested = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "module.py"
    nested.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        module.Path,
        "resolve",
        lambda *a, **k: nested,
        raising=False,
    )
    return nested


def test_prepare_files_builds_tasks(monkeypatch, tmp_path):
    _patch_module_root_to_tmp(monkeypatch, tmp_path, cm_mod)

    builder = FakeBuilder()
    mgr = cm_mod.CopyManager("decay_widths_fake", builder)

    mgr.prepare_files()

    calls = builder.calls
    assert len(calls) == 7

    template_dir = mgr.template_dir
    target_base = mgr.target_base

    expected = {
        "integration.cpp": target_base / "src" / "integration.cpp",
        "kinematics.cpp":  target_base / "src" / "kinematics.cpp",
        "kinematics.h":    target_base / "include" / "kinematics.h",
        "integration.h":   target_base / "include" / "integration.h",
        "csv_helper.cpp":  target_base / "src" / "csv_helper.cpp",
        "csv_helper.h":    target_base / "include" / "csv_helper.h",
    }

    by_name = {c[0].name: c for c in calls if c[0].name != "Makefile"}
    for name, (_, dest, _) in by_name.items():
        assert dest == expected[name]

    kin_mods = [mods for (src, dest, mods) in calls if src.name == "kinematics.h"][0]
    int_mods = [mods for (src, dest, mods) in calls if src.name == "integration.h"][0]
    assert ("using namespace decay_widths;", "using namespace decay_widths_fake;") in kin_mods
    assert ("using namespace decay_widths;", "using namespace decay_widths_fake;") in int_mods

    mk_src, mk_dest, mk_mods = [c for c in calls if c[0].name == "Makefile"][0]
    assert mk_src == mk_dest == target_base / "Makefile"
    assert ("CXXSTD  = -std=c++17", "CXXSTD  = -std=c++20") in mk_mods


def test_write_file_creates_and_respects_force(tmp_path):
    builder = FakeBuilder()
    mgr = cm_mod.CopyManager("anything", builder)

    cpp_path = tmp_path / "out" / "code.cpp"

    p = mgr.write_file("// v1", cpp_path, force=False)
    assert p.exists() and p.read_text() == "// v1"

    mgr.write_file("// v2", cpp_path, force=False)
    assert cpp_path.read_text() == "// v1"

    mgr.write_file("// v3", cpp_path, force=True)
    assert cpp_path.read_text() == "// v3"
