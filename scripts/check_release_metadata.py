#!/usr/bin/env python3
"""Validate SET-ANUBIS release metadata without importing the package.

The checker is intentionally lightweight so it can run before project
installation in GitHub Actions.  It verifies that the package version, release
date, DOI, licence, contact information, documentation and release workflow all
refer to one coherent release.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:  # pragma: no cover - exercised on bare Python 3.10
        tomllib = None  # type: ignore[assignment]

CONTACT_EMAIL = "anubis-active@cern.ch"
CODEOWNERS_TEAM = "@SET-ANUBIS/maintainers"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?$")
STABLE_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
DOI_PATTERN = re.compile(r"^10\.\d{4,9}(?:\.\d+)?/[A-Za-z0-9:/_;.()\[\]\\-]+$")

RELEASE_CRITICAL_FILES = (
    "README.md",
    "RELEASE.md",
    "GITHUB_RELEASE_SETUP.md",
    "CITATION.cff",
    ".zenodo.json",
    "pyproject.toml",
    "SECURITY.md",
    "SUPPORT.md",
)
RELEASE_PLACEHOLDER_PATTERN = re.compile(
    r"(?im)\b(?:TODO|FIXME|TBD|REPLACE[ _-]?ME)\b|"
    r"DOI\s+after|10\.5281/zenodo\.\.\.|"
    r"(?:your|example)[._-]?(?:name|email|account)?@example\.com|"
    r"<YOUR[_ -][^>]+>"
)


@dataclass(frozen=True)
class ReleaseMetadata:
    version: str
    release_date: str
    doi: str
    license: str
    contact_email: str
    stable: bool
    tag: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "release_date": self.release_date,
            "doi": self.doi,
            "license": self.license,
            "contact_email": self.contact_email,
            "stable": self.stable,
            "tag": self.tag,
        }


class ValidationErrors:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.messages.append(message)

    def equal(self, actual: object, expected: object, label: str) -> None:
        if actual != expected:
            self.messages.append(f"{label}: expected {expected!r}, found {actual!r}")

    def raise_if_any(self) -> None:
        if not self.messages:
            return
        formatted = "\n".join(f"  - {message}" for message in self.messages)
        raise SystemExit(f"Release metadata validation failed:\n{formatted}")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"Required release file is missing: {path}") from exc


def _toml_string(section: str, key: str) -> str | None:
    match = re.search(rf'(?m)^{re.escape(key)}\s*=\s*["\']([^"\']+)["\']\s*$', section)
    return match.group(1) if match else None


def _toml_section(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^\[{re.escape(name)}\]\s*$(.*?)(?=^\[|\Z)",
        text,
    )
    return match.group(1) if match else ""


def _load_project(path: Path) -> dict[str, Any]:
    text = _read(path)
    if tomllib is not None:
        return tomllib.loads(text).get("project", {})

    project_section = _toml_section(text, "project")
    urls_section = _toml_section(text, "project.urls")
    maintainers_match = re.search(
        r"(?ms)^maintainers\s*=\s*\[(.*?)^\]\s*$", project_section
    )
    maintainer_block = maintainers_match.group(1) if maintainers_match else ""
    maintainers = [
        {"email": email}
        for email in re.findall(r'email\s*=\s*["\']([^"\']+)["\']', maintainer_block)
    ]
    urls = {
        key: value
        for key, value in re.findall(
            r'(?m)^([A-Za-z][A-Za-z0-9_-]*)\s*=\s*["\']([^"\']+)["\']\s*$',
            urls_section,
        )
    }
    return {
        "name": _toml_string(project_section, "name"),
        "version": _toml_string(project_section, "version"),
        "license": _toml_string(project_section, "license"),
        "maintainers": maintainers,
        "urls": urls,
    }


def _top_level_yaml_scalar(text: str, key: str) -> str | None:
    match = re.search(
        rf"(?m)^{re.escape(key)}:\s*(?:\"([^\"]*)\"|'([^']*)'|([^#\n]+?))\s*$",
        text,
    )
    if not match:
        return None
    return next(value.strip() for value in match.groups() if value is not None)


def _source_version(text: str) -> str | None:
    match = re.search(r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']\s*$', text)
    return match.group(1) if match else None


def _docs_version(text: str) -> tuple[str | None, str | None]:
    match = re.search(
        r'(?m)^version\s*=\s*release\s*=\s*["\']([^"\']+)["\']\s*$', text
    )
    if match:
        return match.group(1), match.group(1)
    version_match = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)["\']\s*$', text)
    release_match = re.search(r'(?m)^release\s*=\s*["\']([^"\']+)["\']\s*$', text)
    return (
        version_match.group(1) if version_match else None,
        release_match.group(1) if release_match else None,
    )


def _changelog_release(text: str) -> tuple[str | None, str | None]:
    match = re.search(
        r"(?m)^##\s+\[?([^\]\s]+)\]?\s+-\s+(\d{4}-\d{2}-\d{2})\s*$",
        text,
    )
    return (match.group(1), match.group(2)) if match else (None, None)


def _normalise_tag(tag: str | None) -> str | None:
    if tag:
        return tag.strip()
    if os.getenv("GITHUB_REF_TYPE") == "tag":
        return os.getenv("GITHUB_REF_NAME", "").strip() or None
    return None


def validate_repository(root: Path, *, tag: str | None = None) -> ReleaseMetadata:
    root = root.resolve()
    errors = ValidationErrors()

    project = _load_project(root / "pyproject.toml")
    version = str(project.get("version", ""))
    license_name = str(project.get("license", ""))
    errors.equal(project.get("name"), "SetAnubis", "pyproject project name")
    errors.require(bool(VERSION_PATTERN.fullmatch(version)), f"invalid release version: {version!r}")
    errors.equal(license_name, "GPL-3.0-or-later", "pyproject licence")

    maintainers = project.get("maintainers", [])
    maintainer_emails = {
        str(item.get("email", "")).strip()
        for item in maintainers
        if isinstance(item, dict) and item.get("email")
    }
    errors.require(
        CONTACT_EMAIL in maintainer_emails,
        f"pyproject maintainers must include {CONTACT_EMAIL}",
    )

    version_source = _source_version(_read(root / "setanubis/SetAnubis/_version.py"))
    errors.equal(version_source, version, "SetAnubis/_version.py version")

    cff_text = _read(root / "CITATION.cff")
    cff_version = _top_level_yaml_scalar(cff_text, "version")
    release_date = _top_level_yaml_scalar(cff_text, "date-released") or ""
    cff_license = _top_level_yaml_scalar(cff_text, "license")
    doi = _top_level_yaml_scalar(cff_text, "doi") or ""
    errors.equal(cff_version, version, "CITATION.cff version")
    errors.equal(_top_level_yaml_scalar(cff_text, "type"), "software", "CITATION.cff type")
    errors.equal(cff_license, license_name, "CITATION.cff licence")
    errors.require(
        bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", release_date)),
        f"invalid CITATION.cff release date: {release_date!r}",
    )
    errors.require(bool(DOI_PATTERN.fullmatch(doi)), f"invalid CITATION.cff DOI: {doi!r}")

    zenodo = json.loads(_read(root / ".zenodo.json"))
    errors.equal(str(zenodo.get("version", "")), version, ".zenodo.json version")
    errors.equal(
        str(zenodo.get("publication_date", "")),
        release_date,
        ".zenodo.json publication date",
    )
    errors.equal(str(zenodo.get("license", "")), license_name, ".zenodo.json licence")
    creator_roles = {
        str(item.get("name")): str(item.get("type"))
        for item in zenodo.get("creators", [])
        if isinstance(item, dict)
    }
    errors.equal(
        creator_roles,
        {
            "Reymermier, Théo": "ProjectLeader",
            "Swallow, Paul": "ProjectManager",
        },
        ".zenodo.json creator roles",
    )
    errors.require(
        "doi" not in zenodo,
        ".zenodo.json should not set its own Zenodo-reserved DOI; the draft owns it",
    )

    changelog_version, changelog_date = _changelog_release(_read(root / "CHANGELOG.md"))
    errors.equal(changelog_version, version, "CHANGELOG latest version")
    errors.equal(changelog_date, release_date, "CHANGELOG release date")

    docs_version, docs_release = _docs_version(_read(root / "Docs/manual/source/conf.py"))
    errors.equal(docs_version, version, "Sphinx version")
    errors.equal(docs_release, version, "Sphinx release")

    dashboard_project = _load_project(
        root / "setanubis/SetAnubis/SetAnubisDBDashboard/pyproject.toml"
    )
    errors.equal(
        dashboard_project.get("version"),
        version,
        "standalone database-dashboard version",
    )

    doi_url = f"https://doi.org/{doi}"
    project_urls = project.get("urls", {})
    errors.equal(project_urls.get("Archive"), doi_url, "pyproject Archive URL")

    readme = _read(root / "README.md")
    errors.require(doi in readme, "README does not contain the release DOI")
    errors.require(doi_url in readme, "README does not link to the DOI resolver")
    errors.require("DOI%20after" not in readme, "README still contains the temporary DOI badge")
    errors.require(
        "10.5281/zenodo..." not in readme,
        "README still contains the abbreviated Zenodo DOI placeholder",
    )

    for relative in ("SECURITY.md", "SUPPORT.md", "setanubis/SetAnubis/branding.py"):
        errors.require(
            CONTACT_EMAIL in _read(root / relative),
            f"{relative} does not contain the shared contact email",
        )

    for relative in RELEASE_CRITICAL_FILES:
        match = RELEASE_PLACEHOLDER_PATTERN.search(_read(root / relative))
        errors.require(
            match is None,
            f"{relative} contains a release placeholder: {match.group(0)!r}"
            if match
            else "",
        )

    codeowners_lines = [
        line.strip()
        for line in _read(root / ".github/CODEOWNERS").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    errors.equal(codeowners_lines, [f"* {CODEOWNERS_TEAM}"], "CODEOWNERS default owner")

    workflow = _read(root / ".github/workflows/release.yml")
    errors.require('- "v*"' in workflow, "release workflow is not triggered by v* tags")
    errors.require("workflow_dispatch:" not in workflow, "release workflow still permits manual dispatch")
    errors.require(
        "python scripts/check_release_metadata.py" in workflow,
        "release workflow does not call the shared metadata checker",
    )
    errors.require("environment: testpypi" in workflow, "TestPyPI environment is missing")
    errors.require("environment: pypi" in workflow, "PyPI environment is missing")
    workflow_jobs = ("publish-testpypi:", "verify-testpypi:", "publish-pypi:")
    errors.require(
        all(name in workflow for name in workflow_jobs),
        "release workflow is missing a publication job",
    )
    errors.require(
        workflow.find(workflow_jobs[0])
        < workflow.find(workflow_jobs[1])
        < workflow.find(workflow_jobs[2]),
        "release workflow does not preserve TestPyPI verification before PyPI",
    )

    release_docs = _read(root / "RELEASE.md")
    errors.require(
        "\ngh workflow run release.yml" not in release_docs,
        "RELEASE.md still instructs maintainers to start a duplicate manual workflow",
    )
    errors.require(doi in release_docs, "RELEASE.md does not record the reserved Zenodo DOI")

    errors.require(not (root / "Assets/Test").exists(), "Assets/Test must not be present in the release tree")
    errors.require(
        "/Assets/Test/" in _read(root / ".gitignore"),
        ".gitignore must exclude /Assets/Test/",
    )

    selected_tag = _normalise_tag(tag)
    if selected_tag is not None:
        errors.equal(selected_tag, f"v{version}", "release tag")

    errors.raise_if_any()
    return ReleaseMetadata(
        version=version,
        release_date=release_date,
        doi=doi,
        license=license_name,
        contact_email=CONTACT_EMAIL,
        stable=bool(STABLE_VERSION_PATTERN.fullmatch(version)),
        tag=selected_tag,
    )


def _write_github_output(path: Path, metadata: ReleaseMetadata) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"version={metadata.version}\n")
        handle.write(f"promote={'true' if metadata.stable else 'false'}\n")
        handle.write(f"doi={metadata.doi}\n")
        handle.write(f"release_date={metadata.release_date}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (default: parent of scripts/)",
    )
    parser.add_argument("--tag", help="expected Git tag, for example v1.0.0")
    parser.add_argument("--github-output", type=Path, help="append workflow outputs to this file")
    parser.add_argument("--json-output", type=Path, help="write validated release metadata as JSON")
    parser.add_argument("--print-version", action="store_true", help="print only the package version")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata = validate_repository(args.root, tag=args.tag)

    if args.github_output:
        _write_github_output(args.github_output, metadata)
    if args.json_output:
        args.json_output.write_text(
            json.dumps(metadata.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.print_version:
        print(metadata.version)
    else:
        print(
            "Release metadata OK: "
            f"SetAnubis {metadata.version}, {metadata.release_date}, DOI {metadata.doi}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
