"""Smoke test for the generic Pythia CMND/runtime interface.

This script is intentionally split in two parts:

1. A pure-Python smoke test that does not require Pythia/HepMC3.  It validates
   that arbitrary particles can be configured in the CMND generator and that the
   Pythia run wrapper can be imported even when the optional C++ binding is absent.
2. An optional runtime test, enabled with ``--run-pythia``, that requires the
   compiled ``pythia_sim`` pybind11 module plus Pythia8 and HepMC3.

Usage from the repository root:

    python main_test_pythia.py
    python main_test_pythia.py --pid 35 --out /tmp/setanubis_pythia_smoke
    python main_test_pythia.py --run-pythia --cmnd path/to/card.cmnd --events 10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable


def _ensure_source_tree_on_path() -> None:
    """Let the script run directly from a checkout without editable install."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "setanubis"
        if (candidate / "SetAnubis" / "__init__.py").exists():
            sys.path.insert(0, str(candidate))
            return


_ensure_source_tree_on_path()

from SetAnubis.core.Pythia.adapters.input.PythiaCMNDInterface import PythiaCMNDInterface
from SetAnubis.core.Pythia.adapters.input.PythiaRunInterface import PythiaRunInterface


class FakeSetAnubisInterface:
    """Small stand-in for SetAnubisInterface used by the pure Python test."""

    def __init__(self, pid: int, mass: float = 10.0):
        self.pid = int(pid)
        self.mass = float(mass)
        self.particles = {
            self.pid: {
                "name": f"X{abs(self.pid)}",
                "antiname": f"X{abs(self.pid)}bar",
                "spin": 2,
                "charge": 0,
                "color": 1,
            }
        }

    def get_all_particles(self) -> dict[int, dict]:
        return self.particles

    def get_particle_info(self, particle: int) -> dict:
        return self.particles[int(particle)]

    def get_particle_mass(self, particle: int) -> complex:
        if int(particle) != self.pid:
            raise KeyError(particle)
        return complex(self.mass, 0.0)


class FakeDecayInterface:
    """Small stand-in for DecayInterface used by the pure Python test."""

    def __init__(self, pid: int):
        self.pid = int(pid)
        self.nsa = None
        self.decays = {(13, -13): 1.0}

    def calculate_lifetime(self, mother: int, unit) -> float:
        return 123.0

    def get_decay_tot(self, particle: int) -> float:
        return 1.0e-12

    def get_all_decays(self, mother: int | None = None) -> Iterable[tuple[int, ...]]:
        if mother is None:
            return [(self.pid, daughters) for daughters in self.decays]
        if int(mother) != self.pid:
            return []
        return list(self.decays)

    def get_br(self, mother: int, daughters: tuple[int, ...]) -> float:
        return self.decays[tuple(daughters)]


def build_generic_cmnd(pid: int) -> str:
    master = FakeSetAnubisInterface(pid=pid)
    decay = FakeDecayInterface(pid=pid)
    interface = PythiaCMNDInterface(master, decay)

    interface.add_pythia_setting("PhaseSpace:pTHatMin", 20)
    interface.add_hard_production("WeakSingleBoson:ffbar2gmZ", "on")
    interface.set_particle_options(
        pid,
        tau0=42.0,
        tauCalc=False,
        mWidth=1.0e-12,
        mMin=0.0,
        mMax=0.0,
        mayDecay=True,
        isVisible=False,
        doForceWidth=True,
    )
    interface.add_particle_setting(pid, "onMode", "off")
    interface.add_new_particles([pid])
    interface.add_decay_from_bsm_particles(pid)
    return interface.serialize()


def assert_cmnd_is_generic(cmnd_text: str, pid: int) -> None:
    required = [
        f"{pid}:new",
        f"{pid}:tau0 = 42.0",
        f"{pid}:mWidth = 1e-12",
        f"{pid}:isVisible = off",
        "PhaseSpace:pTHatMin = 20",
        "WeakSingleBoson:ffbar2gmZ = on",
        f"{pid}:addChannel = 1 1.0 0 13 -13",
    ]
    missing = [item for item in required if item not in cmnd_text]
    if missing:
        raise AssertionError("Missing expected CMND lines: " + ", ".join(missing))

    if pid != 9900012 and "9900012" in cmnd_text:
        raise AssertionError("Found hard-coded HNL PID 9900012 in a generic-particle CMND card")


def run_optional_pythia(args: argparse.Namespace, out_dir: Path, generated_cmnd: Path) -> None:
    runner = PythiaRunInterface(
        str(out_dir / "runtime"),
        new_particles=[args.pid],
        pythia_settings=["Next:numberShowEvent = 0"],
        lifetimes={args.pid: 42.0},
        widths={args.pid: 1.0e-12},
        hard_cuts=[] if args.no_hard_cut else [
            {
                "pdg_id": args.pid,
                "min_pt": args.min_pt,
                "min_count": 1,
                "use_abs_id": True,
                "final_only": False,
            }
        ],
        max_trials=args.max_trials,
        fix_decay_masses=False,
    )

    diagnostic = runner.check_runtime()
    print("Pythia binding diagnostic:", diagnostic)
    if not diagnostic["available"]:
        raise RuntimeError(diagnostic["error"])

    cmnd = Path(args.cmnd) if args.cmnd else generated_cmnd
    runner.process_file(
        config_file=str(cmnd),
        output_lhe_dir=str(out_dir / "runtime" / "lhe"),
        output_hepmc_dir=str(out_dir / "runtime" / "hepmc"),
        output_text_dir=str(out_dir / "runtime" / "text"),
        num_events=args.events,
        suffix="smoke",
        particle_ids=[args.pid],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SetAnubis generic Pythia smoke test")
    parser.add_argument("--pid", type=int, default=42, help="arbitrary particle PDG id used by the smoke test")
    parser.add_argument("--out", default="pythia_smoke_outputs", help="output directory")
    parser.add_argument("--run-pythia", action="store_true", help="also run the compiled C++/Pythia binding")
    parser.add_argument("--cmnd", default=None, help="optional CMND file for the runtime test")
    parser.add_argument("--events", type=int, default=5, help="number of events for --run-pythia")
    parser.add_argument("--max-trials", type=int, default=1000, help="trial budget for hard-cut filtering")
    parser.add_argument("--min-pt", type=float, default=0.0, help="min pT for the optional runtime hard cut")
    parser.add_argument("--no-hard-cut", action="store_true", help="disable runtime hard cut when --run-pythia is used")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmnd_text = build_generic_cmnd(args.pid)
    assert_cmnd_is_generic(cmnd_text, args.pid)

    cmnd_path = out_dir / f"generic_pid_{args.pid}.cmnd"
    cmnd_path.write_text(cmnd_text, encoding="utf-8")
    print(f"OK: generic CMND smoke test passed for PID {args.pid}")
    print(f"Wrote: {cmnd_path}")

    runner = PythiaRunInterface(str(out_dir / "runtime"), new_particles=[args.pid])
    diagnostic = runner.check_runtime()
    if diagnostic["available"]:
        print(f"OK: pythia_sim binding importable from {diagnostic['path']}")
    else:
        print("SKIP: pythia_sim binding is not importable; pure-Python checks still passed")
        print(diagnostic["error"])

    if args.run_pythia:
        run_optional_pythia(args, out_dir, cmnd_path)
        print("OK: optional Pythia runtime test completed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
