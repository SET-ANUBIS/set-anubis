"""Release contracts for branching-ratio adapters and developer tooling."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import SetAnubis.core.BranchingRatio.adapters.output.BRCalculatorLoader as loader_mod
import SetAnubis.core.BranchingRatio.adapters.output.DecayCacheAdapter as cache_mod
import SetAnubis.core.BranchingRatio.adapters.output.MartyFileCopyBuilder as copy_mod
import SetAnubis.core.BranchingRatio.domain.MartyUtil as util_mod


def test_all_branching_ratio_modules_and_public_members_have_docstrings():
    """Keep the complete maintained branching-ratio API self-documenting."""
    root = Path(__file__).parents[3] / "SetAnubis/core/BranchingRatio"
    missing: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if "app" in path.parts or "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if not ast.get_docstring(tree):
            missing.append(f"{path.relative_to(root)}:module")
        for node in tree.body:
            if not isinstance(
                node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            if node.name.startswith("_"):
                continue
            if not ast.get_docstring(node):
                missing.append(f"{path.relative_to(root)}:{node.name}")
            if isinstance(node, ast.ClassDef):
                for member in node.body:
                    if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if member.name.startswith("_"):
                        continue
                    if not ast.get_docstring(member):
                        missing.append(
                            f"{path.relative_to(root)}:{node.name}.{member.name}"
                        )
    assert not missing, "Missing branching-ratio documentation:\n" + "\n".join(missing)


def test_python_calculator_loader_validates_file_and_class_count(tmp_path):
    """Accept exactly one concrete calculator and reject ambiguous scripts."""
    valid = tmp_path / "valid.py"
    valid.write_text(
        "from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation\n"
        "class Calculator(IDecayCalculation):\n"
        "    def calculate(self, mother, daughters, parameters): return 0.25\n",
        encoding="utf-8",
    )
    calculator = loader_mod.BRCalculatorLoader.load_calculator(str(valid))
    assert calculator.calculate(1, [], {}) == pytest.approx(0.25)

    with pytest.raises(FileNotFoundError):
        loader_mod.BRCalculatorLoader.load_calculator(str(tmp_path / "missing.py"))

    empty = tmp_path / "empty.py"
    empty.write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No IDecayCalculation"):
        loader_mod.BRCalculatorLoader.load_calculator(str(empty))

    ambiguous = tmp_path / "ambiguous.py"
    ambiguous.write_text(
        "from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation\n"
        "class First(IDecayCalculation):\n"
        "    def calculate(self, mother, daughters, parameters): return 1\n"
        "class Second(IDecayCalculation):\n"
        "    def calculate(self, mother, daughters, parameters): return 2\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Multiple IDecayCalculation"):
        loader_mod.BRCalculatorLoader.load_calculator(str(ambiguous))


def test_decay_cache_and_marty_copy_facades(monkeypatch, tmp_path):
    """Forward cache retrieval and MARTY copy operations to their backends."""

    class FakeProvider:
        def __init__(self, path):
            self.path = path

        def get_caches(self):
            return {"path": self.path}

    monkeypatch.setattr(cache_mod, "DecayProvider", FakeProvider)
    assert cache_mod.DecayCacheAdapter("/trusted/ufo").get() == {"path": "/trusted/ufo"}

    calls: list[tuple] = []

    class FakeBuilder:
        def add_file(self, src, dest, modifications):
            calls.append((Path(src), Path(dest), modifications))
            return self

        def execute(self):
            calls.append(("execute",))

    monkeypatch.setattr(copy_mod, "FileCopyBuilder", FakeBuilder)
    builder = copy_mod.MartyFileCopyBuilder()
    assert (
        builder.add_file(tmp_path / "a", tmp_path / "b", [("x", "y")])
        is builder.builder
    )
    builder.execute()
    assert calls[-1] == ("execute",)


def test_real_mapping_loaders_and_process_names(monkeypatch, tmp_path):
    """Merge JSON/YAML mappings, reverse them, and build stable process names."""
    assets = tmp_path / "model"
    assets.mkdir()
    (assets / "conversion_sm.json").write_text(
        '[{"name": "alpha0", "ufo_name": "aEWM1"}]', encoding="utf-8"
    )
    (assets / "conversion_model.yaml").write_text(
        "- name: Ve1\n  ufo_name: VeN1\n", encoding="utf-8"
    )
    (assets / "sm_particle.json").write_text(
        '[{"pdg_code": 23, "name": "Z"}]', encoding="utf-8"
    )
    (assets / "model_particle.yaml").write_text(
        "- pdg_code: 9900012\n  name: N1\n", encoding="utf-8"
    )
    monkeypatch.setattr(util_mod, "_model_assets_path", lambda: assets)
    util_mod._load_ufo_mappings.cache_clear()
    util_mod._load_particle_mappings.cache_clear()

    assert util_mod.load_ufo_mappings() == {"alpha0": "aEWM1", "Ve1": "VeN1"}
    assert util_mod.load_ufo_mappings(True)["aEWM1"] == "alpha0"
    assert util_mod.load_particle_mappings() == {"23": "Z", "9900012": "N1"}
    assert util_mod.load_particle_mappings(True)["N1"] == "9900012"
    assert util_mod.decay_name([23], [5, -5], object(), {}) == "23_s_5_5"
    util_mod._load_ufo_mappings.cache_clear()
    util_mod._load_particle_mappings.cache_clear()


def test_packaged_marty_mappings_do_not_depend_on_repository_cwd(monkeypatch, tmp_path):
    """Resolve MARTY mappings from package resources outside the checkout CWD."""
    monkeypatch.chdir(tmp_path)
    util_mod._load_ufo_mappings.cache_clear()
    util_mod._load_particle_mappings.cache_clear()

    assert util_mod.load_particle_mappings()["23"] == "Z"
    assert util_mod.load_ufo_mappings()["M_Z"] == "MZ"
