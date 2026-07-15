"""Create a deterministic Pythia CMND card without the native runtime."""

from __future__ import annotations

import argparse
from pathlib import Path

from SetAnubis.examples.Pythia.dev_examples.main_test_pythia_refactor import (
    assert_cmnd_is_generic,
    build_generic_cmnd,
)

from _common import ensure_output_dir, sha256_file, write_json


def run(output_dir: str | Path) -> dict:
    output = ensure_output_dir(output_dir)
    pid = 42
    text = build_generic_cmnd(pid)
    assert_cmnd_is_generic(text, pid)

    card_path = output / "generic_pid_42.cmnd"
    card_path.write_text(text, encoding="utf-8")
    summary = {
        "particle_pdg": pid,
        "card_file": card_path.name,
        "line_count": len(text.splitlines()),
        "sha256": sha256_file(card_path),
        "native_pythia_executed": False,
    }
    write_json(output / "pythia_cmnd_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reproducibility_outputs/pythia")
    args = parser.parse_args()
    print(run(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
