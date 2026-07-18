"""Backward-compatible wrapper for the CPC reproducibility runner."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SOURCE_ROOT = REPOSITORY_ROOT / "setanubis"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from reproducibility.run_reproducibility import main

if __name__ == "__main__":
    sys.argv = ["--output-root" if arg == "--output-dir" else arg for arg in sys.argv]
    raise SystemExit(main())
