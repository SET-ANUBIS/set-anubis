#!/usr/bin/env python3
"""Run the repeatable SET-ANUBIS checks used after each patch.

The default mode is intentionally fast.  ``--full`` executes the complete
release-candidate gate, including security audits, coverage, reproducibility,
documentation and package construction.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(command: list[str]) -> None:
    print("\n+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def remove_release_outputs() -> None:
    for relative in ("build", "dist"):
        shutil.rmtree(ROOT / relative, ignore_errors=True)
    for path in list(ROOT.glob("*.egg-info")) + list((ROOT / "setanubis").glob("*.egg-info")):
        shutil.rmtree(path, ignore_errors=True)


def quick_checks() -> None:
    run([PYTHON, "scripts/check_release_metadata.py"])
    run(
        [
            PYTHON,
            "-m",
            "compileall",
            "-q",
            "scripts",
            "setanubis/SetAnubis",
            "setanubis/setanubis.py",
            "setanubis/__init__.py",
        ]
    )
    run([PYTHON, "-m", "ruff", "check", "."])
    run(
        [
            PYTHON,
            "-m",
            "pytest",
            "-q",
            "setanubis/tests/unit/test_release_metadata_unit.py",
            "setanubis/tests/unit/common/test_branding_unit.py",
        ]
    )
    run(
        [
            PYTHON,
            "-m",
            "pytest",
            "-q",
            "setanubis/tests/unit/test_public_api_contract.py",
            "-k",
            "final_release_workflow or release_workflow_is_tag_driven",
        ]
    )


def full_checks(*, skip_dependency_audit: bool = False) -> None:
    if not skip_dependency_audit:
        run([PYTHON, "-m", "pip_audit", "--local", "--skip-editable"])
    run(
        [
            PYTHON,
            "-m",
            "bandit",
            "-q",
            "-lll",
            "-r",
            "setanubis/SetAnubis/core",
            "-x",
            ",".join(
                [
                    "setanubis/SetAnubis/core/UFOInterface/SM_NLO",
                    "setanubis/SetAnubis/core/BranchingRatio/app",
                    "setanubis/SetAnubis/core/DataBase/app",
                    "setanubis/SetAnubis/core/Geometry/app",
                    "setanubis/SetAnubis/core/MadGraph/app",
                    "setanubis/SetAnubis/core/Pythia/app",
                    "setanubis/SetAnubis/core/Selection/app",
                ]
            ),
        ]
    )
    run(
        [
            PYTHON,
            "-m",
            "pytest",
            "-q",
            "setanubis/tests",
            "--cov=SetAnubis",
            "--cov-config=pyproject.toml",
            "--cov-report=term-missing",
            "--cov-fail-under=58",
        ]
    )
    run(
        [
            PYTHON,
            "reproducibility/run_reproducibility.py",
            "--output-root",
            ".release-reproducibility",
        ]
    )
    run(["setanubis-pythia-smoke", "--out", ".release-pythia-smoke"])
    run(["setanubis-docs", "--strict"])
    remove_release_outputs()
    run([PYTHON, "-m", "build"])
    distributions = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "dist").iterdir())
    run([PYTHON, "-m", "twine", "check", *distributions])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full",
        action="store_true",
        help="run the complete release-candidate gate after the quick checks",
    )
    parser.add_argument(
        "--skip-dependency-audit",
        action="store_true",
        help="skip pip-audit when the local machine has no network access",
    )
    args = parser.parse_args(argv)

    quick_checks()
    if args.skip_dependency_audit and not args.full:
        parser.error("--skip-dependency-audit requires --full")
    if args.full:
        full_checks(skip_dependency_audit=args.skip_dependency_audit)
    print("\nAll requested SET-ANUBIS checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
