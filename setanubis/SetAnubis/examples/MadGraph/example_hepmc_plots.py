"""Inspect and plot particle kinematics from a user-provided HepMC file."""

from __future__ import annotations

import argparse
from pathlib import Path

from SetAnubis.core.MadGraph.adapters.input.MadGraphHepmcAnalyzer import (
    MadGraphHepmcAnalyzer,
)


def main(argv: list[str] | None = None) -> int:
    """Analyze one HepMC file and display kinematic and relation plots."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hepmc_file", type=Path, help="input HepMC file, optionally gzip-compressed")
    parser.add_argument("--pdg-id", type=int, default=35, help="particle PDG identifier")
    parser.add_argument("--max-events", type=int, default=None)
    parser.add_argument("--bins", type=int, default=60)
    args = parser.parse_args(argv)

    if not args.hepmc_file.is_file():
        parser.error(f"HepMC file does not exist: {args.hepmc_file}")

    analyzer = MadGraphHepmcAnalyzer.from_file(str(args.hepmc_file))
    stats = analyzer.analyze(
        pdg_id=args.pdg_id,
        max_events=args.max_events,
        status=None,
        ignore_self_decays=True,
    )
    print(stats.summary())
    analyzer.plot_all(stats, bins=args.bins, top_n_relations=15)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
