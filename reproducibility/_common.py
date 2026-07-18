"""Shared helpers for the CPC reproducibility suite."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any


def ensure_clean_output_dir(output_dir: str | Path) -> Path:
    """Create an empty output directory while preserving a tracked .gitignore."""
    path = Path(output_dir).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.name == ".gitignore":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    return path


def read_json(path: str | Path) -> Any:
    """Read UTF-8 JSON from *path*."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    """Write stable, human-readable UTF-8 JSON."""
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare_results(actual: Any, expected: Any, path: str = "result") -> None:
    """Recursively compare deterministic results with a small float tolerance."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AssertionError(f"{path}: expected an object, got {type(actual).__name__}")
        if set(actual) != set(expected):
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            raise AssertionError(f"{path}: key mismatch; missing={missing}, extra={extra}")
        for key in expected:
            compare_results(actual[key], expected[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise AssertionError(
                f"{path}: expected a list of length {len(expected)}, got {actual!r}"
            )
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            compare_results(actual_item, expected_item, f"{path}[{index}]")
        return
    if isinstance(expected, float):
        if not math.isclose(float(actual), expected, rel_tol=1e-12, abs_tol=1e-12):
            raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")
        return
    if actual != expected:
        raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")
