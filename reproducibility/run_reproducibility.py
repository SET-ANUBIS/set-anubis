"""Run and validate the five SET-ANUBIS CPC reproducibility scenarios."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SOURCE_ROOT = REPOSITORY_ROOT / "setanubis"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from reproducibility._common import (
    compare_results,
    ensure_clean_output_dir,
    read_json,
    write_json,
)

ROOT = Path(__file__).resolve().parent
SCENARIOS = {
    "R1": "R1_core",
    "R2": "R2_branching_ratio",
    "R3": "R3_pythia_cmnd",
    "R4": "R4_madgraph_cards",
    "R5": "R5_selection",
}


def _normalise_selection(requested: Iterable[str] | None) -> list[tuple[str, str]]:
    if not requested:
        return list(SCENARIOS.items())
    selected = []
    for raw in requested:
        key = raw.upper()
        if key not in SCENARIOS:
            raise ValueError(f"Unknown scenario {raw!r}; choose from {', '.join(SCENARIOS)}")
        selected.append((key, SCENARIOS[key]))
    return selected


def run_suite(
    scenarios: Iterable[str] | None = None,
    output_root: str | Path | None = None,
    validate: bool = True,
) -> dict:
    """Execute selected scenarios, compare summaries, and write an aggregate report."""
    selected = _normalise_selection(scenarios)
    aggregate_root = ensure_clean_output_dir(output_root or ROOT / "output")
    results = {}
    for identifier, directory in selected:
        scenario_dir = ROOT / directory
        scenario_output = (
            aggregate_root / directory if output_root is not None else scenario_dir / "output"
        )
        module = importlib.import_module(f"reproducibility.{directory}.run")
        actual = module.run(scenario_output)
        if validate:
            expected = read_json(scenario_dir / "expected_output/summary.json")
            compare_results(actual, expected, path=identifier)
            (scenario_output / "VALIDATED").write_text(
                f"{identifier} matched expected_output/summary.json.\n",
                encoding="utf-8",
            )
        results[identifier] = actual

    write_json(aggregate_root / "reproducibility_results.json", results)
    if validate:
        (aggregate_root / "VALIDATED").write_text(
            "All requested SET-ANUBIS reproducibility scenarios matched.\n",
            encoding="utf-8",
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        action="append",
        choices=sorted(SCENARIOS),
        help="Run only one scenario; repeat the option to select several.",
    )
    parser.add_argument(
        "--output-root",
        help="Write all scenario outputs below this directory (recommended for CI).",
    )
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()
    results = run_suite(
        scenarios=args.scenario,
        output_root=args.output_root,
        validate=not args.no_validate,
    )
    print(f"Validated {len(results)} reproducibility scenario(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
