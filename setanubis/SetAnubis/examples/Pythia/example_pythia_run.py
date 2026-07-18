"""Run the optional native Pythia interface with a packaged CMND card."""

from __future__ import annotations

import argparse
from pathlib import Path

from SetAnubis.core.Pythia.adapters.input.PythiaRunInterface import PythiaRunInterface
from SetAnubis.examples._runtime import run_example_entrypoint


def main() -> int:
    """Run a small native Pythia sample when the optional binding is available."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=2000, help="Number of events to generate.")
    parser.add_argument("--output-dir", type=Path, default=Path("pythia_outputs"))
    args = parser.parse_args()

    example_dir = Path(__file__).resolve().parent
    interface = PythiaRunInterface(str(args.output_dir))
    output_lhe, output_hepmc = interface.ensure_directories(["lhe", "hepmc"])
    interface.process_file(
        config_file=str(example_dir / "TestFiles" / "test.cmnd"),
        output_lhe_dir=output_lhe,
        output_hepmc_dir=output_hepmc,
        num_events=args.events,
        suffix="test",
        include_time=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
