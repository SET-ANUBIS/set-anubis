"""Release-level contract tests for the documented public API."""

from __future__ import annotations

import ast
import inspect
import io
import tokenize
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
    assert selection.joinpath("example_selection_trace_report.py").is_file()
    assert branching.joinpath("TestFiles/test_BR.csv").is_file()
    for example_name in (
        "example_manual_values_and_lifetime.py",
        "example_python_calculator.py",
        "example_file_interpolation.py",
        "example_ufo_decay_functions.py",
        "example_madgraph_preparation.py",
        "example_marty_preparation.py",
    ):
        assert branching.joinpath(f"dev_examples/{example_name}").is_file()
    assert pythia.joinpath("dev_examples/main_test_pythia_refactor.py").is_file()
    assert (
        resources.files("SetAnubis.examples.ModelCore")
        .joinpath("example_setanubis_interface.py")
        .is_file()
    )
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
            if not isinstance(
                node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
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


def test_all_example_modules_have_explanatory_docstrings():
    """Keep every shipped example self-describing when opened directly."""
    examples = Path(__file__).parents[2] / "SetAnubis" / "examples"
    missing: list[str] = []
    for path in sorted(examples.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if not ast.get_docstring(tree):
            missing.append(str(path.relative_to(examples)))
    assert not missing, "Examples missing module documentation:\n" + "\n".join(missing)


def test_all_example_modules_import_without_running_optional_workflows():
    """Examples should be inspectable without native runtimes or input files."""
    import runpy

    examples = Path(__file__).parents[2] / "SetAnubis" / "examples"
    failures: list[str] = []
    for path in sorted(examples.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            runpy.run_path(str(path), run_name="setanubis_example_import_check")
        except Exception as exc:
            failures.append(
                f"{path.relative_to(examples)}: {type(exc).__name__}: {exc}"
            )
    assert not failures, "Example import failures:\n" + "\n".join(failures)


def test_local_pytest_configuration_preserves_release_gates():
    """Keep tests deterministic when pytest starts inside the source directory."""
    config = Path(__file__).parents[2] / "pytest.ini"
    text = config.read_text(encoding="utf-8")
    assert "testpaths = tests" in text
    assert "error::ResourceWarning" in text
    assert "SwigPyPacked" in text and "swigvarlink" in text


def test_source_tree_contains_no_macos_metadata_files():
    """Prevent AppleDouble and Finder metadata from entering release inputs.

    Generated runtime directories such as ``db/Temp`` are deliberately excluded:
    they are ignored by Git and are never included in the wheel or source
    distribution.  The test focuses on files that can enter a release archive.
    """
    root = Path(__file__).parents[3]
    release_roots = [
        root / ".github",
        root / "Assets",
        root / "Docs",
        root / "External_Integration",
        root / "MacOS",
        root / "reproducibility",
        root / "setanubis",
    ]
    candidates = [path for path in root.iterdir() if path.is_file()]
    for release_root in release_roots:
        if release_root.exists():
            candidates.extend(
                path for path in release_root.rglob("*") if path.is_file()
            )

    metadata = sorted(
        path.relative_to(root)
        for path in candidates
        if path.name.startswith("._") or path.name == ".DS_Store"
    )
    assert not metadata, f"Remove macOS metadata files: {metadata}"


def test_hnl_branching_ratio_table_has_single_canonical_copy():
    """Keep the large HNL branching-ratio table in one packaged location."""
    root = Path(__file__).resolve().parents[2] / "SetAnubis"
    canonical = root / "examples" / "Pythia" / "TestFiles" / "N1_branchingratios.dat"
    duplicates = [
        root / "core" / "Pythia" / "app" / "TestFiles" / "N1_branchingratios.dat",
        root
        / "core"
        / "BranchingRatio"
        / "app"
        / "hnl_files"
        / "N1_branchingratios.dat",
    ]
    assert canonical.is_file()
    assert canonical.stat().st_size > 5_000_000
    existing_duplicates = [path for path in duplicates if path.exists()]
    assert not existing_duplicates, (
        "Remove obsolete HNL table copies; the canonical resource is "
        f"{canonical}: {existing_duplicates}"
    )


def test_selection_examples_use_the_current_geometry_stack():
    """Prevent examples from reintroducing removed geometry or engine adapters."""
    examples = Path(__file__).resolve().parents[2] / "SetAnubis/examples/Selection"
    current_stack_examples = [
        examples / "example_selection_pipeline.py",
        examples / "dev_examples/example_jets_and_pT_deltaR_cuts.py",
    ]
    for example in current_stack_examples:
        source = example.read_text(encoding="utf-8")
        assert "ATLASCavernGeometry.create" in source
        assert "SelectionGeometryAdapter(geometry)" in source
        assert "GeometrySelectionAdapter" not in source
        assert "SelectionEnginev2" not in source


def test_maintained_comments_and_docstrings_are_written_in_english():
    """Keep contributor-facing source documentation consistently in English."""

    root = Path(__file__).parents[2]
    source_roots = [root / "SetAnubis", root / "tests"]
    excluded_parts = {
        "assets",
        "UFOInterface",
    }
    french_markers = (
        "ajoute",
        "supprime",
        "génère",
        "renvoie",
        "remplace",
        "introuvable",
        "détermination",
        "écriture",
        "mère",
        "filles",
        "nœud",
        "dépendances",
        "créer",
        "déjà",
        "utilisez",
        "feuille placeholder",
        "non initialisées",
        "appelle create",
        "fournit",
    )
    failures: list[str] = []

    for source_root in source_roots:
        for path in sorted(source_root.rglob("*.py")):
            if path.resolve() == Path(__file__).resolve():
                continue
            if any(part in excluded_parts for part in path.parts):
                continue
            stream = io.StringIO(path.read_text(encoding="utf-8"))
            for token in tokenize.generate_tokens(stream.readline):
                if token.type not in {tokenize.COMMENT, tokenize.STRING}:
                    continue
                lowered = token.string.lower()
                marker = next(
                    (item for item in french_markers if item in lowered), None
                )
                if marker:
                    failures.append(
                        f"{path.relative_to(root)}:{token.start[0]} contains {marker!r}"
                    )

    assert not failures, "French comments/docstrings remain:\n" + "\n".join(failures)


def test_release_python_files_parse_with_supported_minimum_version():
    """Reject Python syntax that is newer or older than the supported baseline."""
    root = Path(__file__).parents[3]
    release_roots = [
        root / "Assets",
        root / "Docs",
        root / "External_Integration",
        root / "MacOS",
        root / "reproducibility",
        root / "setanubis",
    ]
    python_files = [path for path in root.iterdir() if path.suffix == ".py"]
    for release_root in release_roots:
        if release_root.exists():
            python_files.extend(release_root.rglob("*.py"))

    failures: list[str] = []
    for path in sorted(set(python_files)):
        try:
            ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
                feature_version=(3, 10),
            )
        except (SyntaxError, UnicodeDecodeError) as exc:
            failures.append(f"{path.relative_to(root)}: {exc}")

    assert not failures, "Python 3.10 syntax failures:\n" + "\n".join(failures)
