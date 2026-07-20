"""Release-level contract tests for the documented public API."""

from __future__ import annotations

import ast
import json
import inspect
import io
import tokenize
from importlib import resources
from pathlib import Path

import SetAnubis
import setanubis


def _iter_release_input_files(root: Path):
    """Yield files that can enter the maintained source or binary distributions.

    Downloaded toolchains and local build trees under ``External_Integration``
    are intentionally excluded.  They are ignored by Git and pruned by
    ``MANIFEST.in``; validating third-party generated sources would make the
    release gates depend on whichever local toolchain happened to be built.
    """
    root_files = [path for path in root.iterdir() if path.is_file()]
    maintained_roots = [
        root / ".github",
        root / "Assets",
        root / "Docs",
        root / "MacOS",
        root / "reproducibility",
        root / "setanubis",
    ]
    excluded_prefixes = (
        root / "Assets" / "Test",
        root / "Docs" / "manual" / "build",
    )
    excluded_names = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        "build",
        "dist",
        ".venv",
        "venv",
    }

    yield from root_files
    for maintained_root in maintained_roots:
        if not maintained_root.exists():
            continue
        for path in maintained_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in excluded_names for part in path.parts):
                continue
            if any(path.is_relative_to(prefix) for prefix in excluded_prefixes):
                continue
            yield path

    # Only these small Python helpers are maintained by SetAnubis.  Downloaded
    # Pythia, HepMC3, MadGraph, MARTY and GoogleTest sources are third-party.
    for relative in (
        "External_Integration/MadGraph/madgraph.py",
        "External_Integration/Pythia/test_pythia.py",
    ):
        path = root / relative
        if path.is_file():
            yield path


def test_public_facades_export_the_same_names():
    assert set(SetAnubis.__all__) == set(setanubis.__all__)
    assert SetAnubis.__version__ == setanubis.__version__


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

    for resource_name in (
        "hnl_selection_cutflow.hepmc.gz",
        "hnl_selection_cutflow_df.csv.gz",
        "hnl_selection_cutflow_bundle.pkl.gz",
        "hnl_selection_cutflow_manifest.json",
    ):
        assert selection.joinpath(f"InputFiles/{resource_name}").is_file()
    assert selection.joinpath("example_selection_trace_report.py").is_file()
    assert selection.joinpath("example_real_selection_trace_report.py").is_file()
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
    assert (
        resources.files("SetAnubis.HepMCGUI")
        .joinpath("assets/set-anubis-logo.png")
        .is_file()
    )
    assert (
        resources.files(
            "SetAnubis.SetAnubisDBDashboard.SetAnubisDBDashboard"
        )
        .joinpath("assets/set-anubis-logo.png")
        .is_file()
    )


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
    """Prevent AppleDouble and Finder metadata from entering release inputs."""
    root = Path(__file__).parents[3]
    metadata = sorted(
        path.relative_to(root)
        for path in set(_iter_release_input_files(root))
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
    geometry_sources = [
        examples / "compact_sample.py",
    ]
    for example in geometry_sources:
        source = example.read_text(encoding="utf-8")
        assert "ATLASCavernGeometry.create" in source
        assert "SelectionGeometryAdapter(geometry)" in source

    for example in examples.rglob("*.py"):
        source = example.read_text(encoding="utf-8")
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
    """Reject unsupported syntax in maintained Python release inputs."""
    root = Path(__file__).parents[3]
    python_files = {
        path
        for path in _iter_release_input_files(root)
        if path.suffix == ".py"
    }

    failures: list[str] = []
    for path in sorted(python_files):
        try:
            ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
                feature_version=(3, 10),
            )
        except (SyntaxError, UnicodeDecodeError) as exc:
            failures.append(f"{path.relative_to(root)}: {exc}")

    assert not failures, "Python 3.10 syntax failures:\n" + "\n".join(failures)



def test_all_executable_examples_use_the_shared_banner_entrypoint():
    """Keep direct example execution visually consistent without import side effects."""
    examples = Path(__file__).parents[2] / "SetAnubis" / "examples"
    missing = []
    for path in sorted(examples.rglob("*.py")):
        if "TestFiles" in path.parts or path.name in {"__init__.py", "_runtime.py"}:
            continue
        source = path.read_text(encoding="utf-8")
        if 'if __name__ == "__main__"' not in source:
            continue
        if "run_example_entrypoint" not in source:
            missing.append(str(path.relative_to(examples)))
    assert not missing, "Executable examples missing shared banner wrapper: " + ", ".join(missing)

def test_release_metadata_and_branding_assets_are_consistent():
    """Keep licence metadata and release-facing branding in sync."""
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        import tomli as tomllib

    root = Path(__file__).parents[3]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["license"] == "GPL-3.0-or-later"
    assert "GNU GENERAL PUBLIC LICENSE" in (root / "LICENSE").read_text(
        encoding="utf-8"
    )
    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    assert "license: GPL-3.0-or-later" in citation
    assert "ANUBIS: Projected Sensitivities and Initial Results" in citation
    assert 'url: "https://arxiv.org/abs/2512.14942"' in citation
    assert "SET-ANUBIS proceeding" not in citation

    required_assets = [
        root / "Docs/assets/set-anubis-logo.png",
        root / "Docs/assets/anubis-ceiling-concept.png",
        root / "Docs/manual/source/ProgramOverview.rst",
        root / "Docs/manual/source/_static/set-anubis-logo.png",
        root / "Docs/manual/source/images/set-anubis-logo.png",
        root / "Docs/manual/source/images/anubis-ceiling-concept.png",
        root / ".zenodo.json",
        root / "setanubis/SetAnubis/HepMCGUI/assets/set-anubis-logo.png",
        root
        / "setanubis/SetAnubis/SetAnubisDBDashboard/SetAnubisDBDashboard/assets"
        / "set-anubis-logo.png",
    ]
    missing = [path.relative_to(root) for path in required_assets if not path.is_file()]
    assert not missing, f"Missing release branding assets: {missing}"

    dev_dependencies = project["optional-dependencies"]["dev"]
    assert any(dependency.startswith("tomli") for dependency in dev_dependencies)

    zenodo = json.loads((root / ".zenodo.json").read_text(encoding="utf-8"))
    assert zenodo["license"] == "GPL-3.0-or-later"
    assert zenodo["upload_type"] == "software"
    assert zenodo["version"] == project["version"]
    assert zenodo["creators"] == [
        {"name": "Reymermier, Théo", "type": "ProjectLeader"},
        {"name": "Swallow, Paul", "type": "ProjectManager"},
    ]
    assert {item["name"] for item in zenodo["contributors"]} == {
        "Erner, Sofie",
        "Mullin, Anna",
        "Satterthwaite, Toby",
        "Brandt, Oleg",
    }
    assert all(item["type"] == "ProjectMember" for item in zenodo["contributors"])
    assert any(
        item["identifier"] == "https://arxiv.org/abs/2606.26862"
        for item in zenodo["related_identifiers"]
    )

    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "https://arxiv.org/abs/2606.26862" in readme
    assert "`.zenodo.json`" in readme
    assets_notice = (root / "Docs/assets/README.md").read_text(encoding="utf-8")
    assert "CC BY-NC-ND 4.0" in assets_notice
    assert "without cropping" in assets_notice



def test_reproducibility_suite_has_cpc_scenario_contract():
    """Require independent R1--R5 inputs, outputs and expected results."""
    root = Path(__file__).parents[3]
    reproducibility = root / "reproducibility"
    scenarios = [
        "R1_core",
        "R2_branching_ratio",
        "R3_pythia_cmnd",
        "R4_madgraph_cards",
        "R5_selection",
    ]
    for name in scenarios:
        scenario = reproducibility / name
        assert (scenario / "README.md").is_file()
        assert (scenario / "run.py").is_file()
        assert (scenario / "input/config.json").is_file()
        assert (scenario / "expected_output/summary.json").is_file()
        assert (scenario / "output/.gitignore").read_text(encoding="utf-8") == "*\n!.gitignore\n"

    workflow = (root / ".github/workflows/reproducibility.yml").read_text(
        encoding="utf-8"
    )
    assert "CPC R1-R5" in workflow
    assert "run_reproducibility.py" in workflow
    assert "--output-root reproducibility-output" in workflow
    assert "path: reproducibility-output" in workflow
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    assert "/reproducibility-output/" in gitignore
    release = (root / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "Run CPC reproducibility gate" in release
    assert "--output-root release-reproducibility" in release
    assert "path: release-reproducibility" in release
    assert "/release-reproducibility/" in gitignore

def test_final_release_workflow_requires_a_matching_tag():
    """Prevent final PyPI publication from an untagged branch commit."""
    root = Path(__file__).parents[3]
    workflow = (root / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "refs/tags/v${SETANUBIS_VERSION}" in workflow
    assert "python scripts/check_release_metadata.py" in workflow
    assert "workflow_dispatch:" not in workflow
    assert "environment: testpypi" in workflow
    assert "environment: pypi" in workflow

    workflow_dir = root / ".github/workflows"
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8") for path in workflow_dir.glob("*.yml")
    )
    assert "actions/checkout@v7" not in workflow_text
    assert "actions/checkout@v6" in workflow_text

    docs_workflow = (root / ".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert "paths:" not in docs_workflow


def test_release_workflow_is_tag_driven_and_testpypi_gated():
    """Require TestPyPI verification before any final PyPI promotion."""
    root = Path(__file__).parents[3]
    workflow = (root / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert 'tags:' in workflow and '- "v*"' in workflow
    assert 'needs: [build, publish-testpypi]' in workflow
    assert 'needs: [build, verify-testpypi]' in workflow
    assert "if: needs.build.outputs.promote == 'true'" in workflow
    assert workflow.index('publish-testpypi:') < workflow.index('verify-testpypi:')
    assert workflow.index('verify-testpypi:') < workflow.index('publish-pypi:')
    metadata_checker = (root / "scripts/check_release_metadata.py").read_text(
        encoding="utf-8"
    )
    assert "STABLE_VERSION_PATTERN" in metadata_checker
    assert "promote={'true' if metadata.stable else 'false'}" in metadata_checker


def test_dash_applications_use_packaged_scientific_defaults():
    """Keep both optional interfaces usable immediately after wheel installation."""
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        import tomli as tomllib

    from SetAnubis.HepMCGUI.demo import demo_hepmc_path
    from SetAnubis.HepMCGUI.selection_diagnostics import (
        SELECTION_STAGE_ORDER,
        standard_selection_description,
    )
    from SetAnubis.SetAnubisDBDashboard.SetAnubisDBDashboard.data import (
        load_payload,
    )
    from SetAnubis.SetAnubisDBDashboard.SetAnubisDBDashboard.demo import (
        ensure_demo_workspace,
    )

    hepmc = demo_hepmc_path()
    assert hepmc.is_file()
    assert hepmc.name == "hnl_selection_cutflow.hepmc.gz"
    assert SELECTION_STAGE_ORDER == [
        "Original",
        "LLPDecay",
        "InCavern",
        "NotInATLAS",
        "Geometry",
        "Tracker",
        "MET",
        "IsoJets",
        "IsoCharged",
        "IsoAll",
        "Final",
    ]
    selection = standard_selection_description()
    assert selection["minimum_met_gev"] == 30.0
    assert selection["minimum_stations"] == 2
    assert selection["minimum_intersections"] == 2

    workspace = ensure_demo_workspace()
    assert workspace.database.is_file()
    assert workspace.storage.is_dir()
    payload = load_payload(
        str(workspace.database),
        str(workspace.storage),
        include_particles=True,
    )
    assert payload["storage"]["events"] == 1
    assert payload["storage"]["events_with_bundles"] == 1
    assert payload["events"][0]["run_name"] == "R5_selection_benchmark"
    assert payload["events"][0]["llp_pid"] == 9900012
    assert payload["particles"][0]["pdg"] == 9900012

    root = Path(__file__).parents[3]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert "pyhepmc" in project["optional-dependencies"]["app"]
    documentation = (root / "Docs/manual/source/DashApplications.rst").read_text(
        encoding="utf-8"
    )
    assert "seven-event HNL benchmark" in documentation
    assert "Packaged" not in documentation or "packaged" in documentation.lower()
    assert "db/Events_THEO" not in documentation


def test_marty_one_to_three_template_uses_safe_sampling_bounds():
    """Prevent out-of-range mass access in generated 1-to-3 kinematics code."""
    root = Path(__file__).parents[3]
    templates = [
        root / "Assets/MARTY/templates/kinematics.cpp",
        root / "Assets/MARTY/templates/kinematics_gpt.cpp",
        root / "setanubis/SetAnubis/assets/MARTY/templates/kinematics.cpp",
        root / "setanubis/SetAnubis/assets/MARTY/templates/kinematics_gpt.cpp",
    ]
    signature = "KinematicsCalculator13::compute_kinematic_limits() const"
    for template in templates:
        source = template.read_text(encoding="utf-8")
        body = source.split(signature, 1)[1].split(
            "KinematicsCalculator13::compute_phase_space_factor", 1
        )[0]
        assert "m_masses[4]" not in body
        assert "return {{0.0, 1.0}, {0.0, 1.0}};" in body
        assert "phase-space boundary" in body
