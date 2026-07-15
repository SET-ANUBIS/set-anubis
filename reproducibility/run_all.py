"""Run and validate all lightweight CPC reproducibility examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import branching_ratio_example
import core_example
import madgraph_cards_example
import pythia_cmnd_example
import selection_example
from _common import ensure_output_dir, write_json


def _compare(actual, expected, path="results") -> None:
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise AssertionError(f"{path}: keys differ: {set(actual) ^ set(expected)}")
        for key in expected:
            _compare(actual[key], expected[key], f"{path}.{key}")
        return
    if isinstance(expected, float):
        if abs(float(actual) - expected) > 1e-12 * max(1.0, abs(expected)):
            raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")
        return
    if actual != expected:
        raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")


def run_all(output_dir: str | Path, validate: bool = True) -> dict:
    root = ensure_output_dir(output_dir)
    results = {
        "core": core_example.run(root / "core"),
        "branching_ratio": branching_ratio_example.run(root / "branching_ratio"),
        "pythia": pythia_cmnd_example.run(root / "pythia"),
        "madgraph": madgraph_cards_example.run(root / "madgraph"),
        "selection": selection_example.run(root / "selection"),
    }
    write_json(root / "results.json", results)

    if validate:
        expected_path = Path(__file__).resolve().parent / "expected_results.json"
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        _compare(results, expected)
        (root / "VALIDATED").write_text("All expected results matched.\n", encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reproducibility_outputs")
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()
    run_all(args.output_dir, validate=not args.no_validate)
    print(f"Reproducibility outputs written to {Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
