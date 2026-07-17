"""Release-level contract tests for the documented public API."""

from __future__ import annotations

import ast
import inspect
from importlib import resources
from pathlib import Path

import SetAnubis
import setanubis


def test_public_facades_export_the_same_names():
    assert set(SetAnubis.__all__) == set(setanubis.__all__)
    assert SetAnubis.__version__ == setanubis.__version__ == "1.0.0"


def test_every_public_export_imports_and_has_documentation():
    failures: list[str] = []
    for name in SetAnubis.__all__:
        if name == "__version__":
            continue
        try:
            value = getattr(SetAnubis, name)
        except Exception as exc:  # pragma: no cover - reported with context below
            failures.append(f"{name}: import failed: {type(exc).__name__}: {exc}")
            continue
        if not inspect.getdoc(value):
            failures.append(f"{name}: missing public docstring")
    assert not failures, "\n".join(failures)


def test_required_examples_and_data_are_packaged():
    selection = resources.files("SetAnubis.examples.Selection")
    branching = resources.files("SetAnubis.examples.BranchingRatio")
    pythia = resources.files("SetAnubis.examples.Pythia")

    assert selection.joinpath("InputFiles/hnl_df.csv").is_file()
    assert branching.joinpath("TestFiles/test_BR.csv").is_file()
    assert pythia.joinpath("dev_examples/main_test_pythia_refactor.py").is_file()
    assert resources.files("SetAnubis.examples.ModelCore").joinpath(
        "example_setanubis_interface.py"
    ).is_file()
    assert SetAnubis.ufo_path("UFO_HNL").joinpath("write_param_card.py").is_file()


def test_architecture_interfaces_have_class_and_method_docstrings():
    core = Path(__file__).parents[2] / "SetAnubis" / "core"
    interface_files = {path for path in core.rglob("ports/*.py")}
    interface_files.update(path for path in core.rglob("ports/**/*.py"))
    interface_files.update(path for path in core.rglob("domain/I*.py"))

    missing: list[str] = []
    for path in sorted(interface_files):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_"):
                continue
            if not ast.get_docstring(node):
                missing.append(f"{path.relative_to(core)}:{node.name}")
            if isinstance(node, ast.ClassDef):
                for member in node.body:
                    if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if member.name.startswith("_"):
                        continue
                    if not ast.get_docstring(member):
                        missing.append(
                            f"{path.relative_to(core)}:{node.name}.{member.name}"
                        )

    assert not missing, "Missing interface docstrings:\n" + "\n".join(missing)


def test_hnl_branching_ratio_table_has_single_canonical_copy():
    """Keep the large HNL branching-ratio table in one packaged location."""
    root = Path(__file__).resolve().parents[2] / "SetAnubis"
    canonical = root / "examples" / "Pythia" / "TestFiles" / "N1_branchingratios.dat"
    duplicates = [
        root / "core" / "Pythia" / "app" / "TestFiles" / "N1_branchingratios.dat",
        root / "core" / "BranchingRatio" / "app" / "hnl_files" / "N1_branchingratios.dat",
    ]
    assert canonical.is_file()
    assert canonical.stat().st_size > 5_000_000
    assert not any(path.exists() for path in duplicates)
