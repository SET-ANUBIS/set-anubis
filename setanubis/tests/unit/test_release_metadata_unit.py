"""Tests for the repository-level release metadata checker."""

from __future__ import annotations

import json
import runpy
import types
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[3]
CHECKER = ROOT / "scripts/check_release_metadata.py"
RELEASE_CONTRACT_FILES = (
    "pyproject.toml",
    "CITATION.cff",
    ".zenodo.json",
    "CHANGELOG.md",
    "README.md",
    "RELEASE.md",
    "GITHUB_RELEASE_SETUP.md",
    "SECURITY.md",
    "SUPPORT.md",
    ".gitignore",
    ".github/CODEOWNERS",
    ".github/workflows/release.yml",
    "Docs/manual/source/conf.py",
    "setanubis/SetAnubis/_version.py",
    "setanubis/SetAnubis/branding.py",
    "setanubis/SetAnubis/SetAnubisDBDashboard/pyproject.toml",
)


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_release_metadata_checker_accepts_repository_state():
    result = _run()
    assert result.returncode == 0, result.stderr
    assert "Release metadata OK" in result.stdout
    assert "10.5281/zenodo.21462101" in result.stdout


def test_release_metadata_checker_writes_machine_readable_outputs(tmp_path):
    version_result = _run("--print-version")
    assert version_result.returncode == 0, version_result.stderr
    version = version_result.stdout.strip()

    github_output = tmp_path / "github-output.txt"
    json_output = tmp_path / "release-metadata.json"
    result = _run(
        "--tag",
        f"v{version}",
        "--github-output",
        str(github_output),
        "--json-output",
        str(json_output),
    )
    assert result.returncode == 0, result.stderr

    outputs = github_output.read_text(encoding="utf-8")
    assert f"version={version}" in outputs
    assert "promote=true" in outputs
    assert "doi=10.5281/zenodo.21462101" in outputs

    metadata = json.loads(json_output.read_text(encoding="utf-8"))
    assert metadata["version"] == version
    assert metadata["tag"] == f"v{version}"
    assert metadata["stable"] is True


def _copy_release_contract(destination: Path) -> Path:
    for relative in RELEASE_CONTRACT_FILES:
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return destination


def test_release_metadata_checker_rejects_a_mismatched_tag():
    result = _run("--tag", "v0.0.0")
    assert result.returncode != 0
    assert "release tag" in result.stderr


def test_release_metadata_checker_rejects_a_placeholder(tmp_path):
    root = _copy_release_contract(tmp_path / "repository")
    readme = root / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\nTODO: publish DOI\n")

    result = _run("--root", str(root))

    assert result.returncode != 0
    assert "release placeholder" in result.stderr


def test_release_metadata_checker_rejects_dashboard_version_drift(tmp_path):
    root = _copy_release_contract(tmp_path / "repository")
    dashboard = root / "setanubis/SetAnubis/SetAnubisDBDashboard/pyproject.toml"
    dashboard.write_text(
        dashboard.read_text(encoding="utf-8").replace(
            'version = "1.0.0"', 'version = "0.1.0"'
        ),
        encoding="utf-8",
    )

    result = _run("--root", str(root))

    assert result.returncode != 0
    assert "standalone database-dashboard version" in result.stderr


def test_optional_pythia_extension_uses_a_relative_source_path(monkeypatch, tmp_path):
    import setuptools

    monkeypatch.setenv("SETANUBIS_BUILD_PYTHIA", "0")
    monkeypatch.setattr(setuptools, "setup", lambda **_: None)
    namespace = runpy.run_path(str(ROOT / "setup.py"))

    namespace["_pythia_extension"].__globals__["_dependency_report"] = lambda: (
        True,
        {
            "pythia8_prefix": str(tmp_path / "pythia8"),
            "pythia8_include": str(tmp_path / "pythia8/include"),
            "pythia8_lib": str(tmp_path / "pythia8/lib"),
            "hepmc3_prefix": str(tmp_path / "hepmc3"),
            "hepmc3_include": str(tmp_path / "hepmc3/include"),
            "hepmc3_lib": str(tmp_path / "hepmc3/lib"),
            "pybind11": "available",
        },
    )
    monkeypatch.setitem(
        sys.modules,
        "pybind11",
        types.SimpleNamespace(get_include=lambda: str(tmp_path / "pybind11/include")),
    )

    extension = namespace["_pythia_extension"]()

    assert extension.sources == ["External_Integration/Pythia/bindings.cpp"]
    assert all(not Path(source).is_absolute() for source in extension.sources)
