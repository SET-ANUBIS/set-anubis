"""Load a user-defined Python decay calculator through the public interface."""

from __future__ import annotations

from SetAnubis.examples._runtime import run_example_entrypoint

from importlib.resources import files

from SetAnubis import (
    CalculationDecayStrategy,
    DecayInterface,
    SetAnubisInterface,
    ufo_path,
)


def python_calculator_path() -> str:
    """Return the packaged demonstration calculator path."""
    return str(
        files("SetAnubis.examples.BranchingRatio").joinpath("TestFiles/test_BR.py")
    )


def configure_python_example(decays: DecayInterface) -> None:
    """Register a channel evaluated by the packaged Python calculator."""
    # The script must define one concrete IDecayCalculation subclass. It is
    # executable Python, so only load files from trusted sources.
    decays.add_decays(
        [{"mother": 25, "daughters": [-12, 12]}],
        CalculationDecayStrategy.PYTHON,
        {"script_path": python_calculator_path(), "BR": False},
    )


def main() -> int:
    """Evaluate the Python-backed width and print the resulting lifetime."""
    model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
    decays = DecayInterface(model)
    configure_python_example(decays)
    print("Python partial width [GeV]:", decays.get_decay(25, [-12, 12]))
    print("Total width [GeV]:", decays.get_decay_tot(25))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
