"""R3: create a deterministic Pythia CMND file without running Pythia."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SOURCE_ROOT = REPOSITORY_ROOT / "setanubis"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from SetAnubis.examples.Pythia.dev_examples.main_test_pythia_refactor import (
    assert_cmnd_is_generic,
    build_generic_cmnd,
)

from reproducibility._common import (
    ensure_clean_output_dir,
    read_json,
    sha256_file,
    write_json,
)

HERE = Path(__file__).resolve().parent


def run(output_dir: str | Path = HERE / "output") -> dict:
    """Generate and validate the command card for the configured particle."""
    config = read_json(HERE / "input/config.json")
    output = ensure_clean_output_dir(output_dir)
    particle_pdg = int(config["particle_pdg"])
    text = build_generic_cmnd(particle_pdg)
    assert_cmnd_is_generic(text, particle_pdg)
    card_path = output / f"generic_pid_{particle_pdg}.cmnd"
    card_path.write_text(text, encoding="utf-8")
    summary = {
        "scenario": "R3_pythia_cmnd",
        "particle_pdg": particle_pdg,
        "card_file": card_path.name,
        "line_count": len(text.splitlines()),
        "sha256": sha256_file(card_path),
        "native_pythia_executed": False,
    }
    write_json(output / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(HERE / "output"))
    args = parser.parse_args()
    print(run(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
