from pathlib import Path
import os
import shutil
import pytest

import SetAnubis.core.BranchingRatio.domain.MartyCopyManager as cm_mod


class CopyingBuilder:
    """Builder d'intégration : applique les remplacements puis écrit dest."""
    def __init__(self):
        self.tasks = []
    def add_file(self, src, dest, modifications):
        self.tasks.append((Path(src), Path(dest), list(modifications)))
    def execute(self):
        for src, dest, mods in self.tasks:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                text = src.read_text(encoding="utf-8")
            else:
                text = ""
            for old, new in mods:
                text = text.replace(old, new)
            dest.write_text(text, encoding="utf-8")


def _patch_root(monkeypatch, tmp_path: Path, module):
    """Force Path(__file__).resolve() à renvoyer un chemin profond dans tmp_path."""
    nested = tmp_path / "p" / "q" / "r" / "s" / "t" / "u" / "module.py"
    nested.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        module.Path,
        "resolve",
        lambda *a, **k: nested,
        raising=False,
    )
    return nested


def test_copy_execute_full_flow(monkeypatch, tmp_path):
    nested = _patch_root(monkeypatch, tmp_path, cm_mod)
    root = (nested.parent.parent.parent.parent.parent.parent)

    templates = root / "Assets" / "MARTY" / "templates"
    templates.mkdir(parents=True, exist_ok=True)

    (templates / "integration.cpp").write_text("// cpp\n", encoding="utf-8")
    (templates / "kinematics.cpp").write_text("// cpp k\n", encoding="utf-8")
    (templates / "kinematics.h").write_text("using namespace decay_widths;\n", encoding="utf-8")
    (templates / "integration.h").write_text("using namespace decay_widths;\n", encoding="utf-8")
    (templates / "csv_helper.cpp").write_text("// csv cpp\n", encoding="utf-8")
    (templates / "csv_helper.h").write_text("// csv h\n", encoding="utf-8")

    target_base = root / "Assets" / "MARTY" / "MartyTemp" / "libs" / "decay_widths_fake"
    target_base.mkdir(parents=True, exist_ok=True)
    (target_base / "Makefile").write_text("CXXSTD  = -std=c++17\n", encoding="utf-8")

    builder = CopyingBuilder()
    mgr = cm_mod.CopyManager("decay_widths_fake", builder)

    mgr.execute()

    inc_dir = target_base / "include"
    src_dir = target_base / "src"
    assert (inc_dir / "kinematics.h").exists()
    assert (inc_dir / "integration.h").exists()
    assert (inc_dir / "csv_helper.h").exists()
    assert (src_dir / "integration.cpp").exists()
    assert (src_dir / "kinematics.cpp").exists()
    assert (src_dir / "csv_helper.cpp").exists()

    assert (inc_dir / "kinematics.h").read_text() == "using namespace decay_widths_fake;\n"
    assert (inc_dir / "integration.h").read_text() == "using namespace decay_widths_fake;\n"
    assert (target_base / "Makefile").read_text() == "CXXSTD  = -std=c++20\n"