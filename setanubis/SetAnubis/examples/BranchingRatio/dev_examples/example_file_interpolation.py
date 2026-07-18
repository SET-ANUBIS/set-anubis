"""Interpolate decay widths or branching ratios from a CSV parameter grid."""

from __future__ import annotations

from SetAnubis.examples._runtime import run_example_entrypoint

from importlib.resources import files

from SetAnubis import (
    CalculationDecayStrategy,
    DecayInterface,
    SetAnubisInterface,
    ufo_path,
)


def table_path() -> str:
    """Return the packaged two-dimensional demonstration table."""
    return str(
        files("SetAnubis.examples.BranchingRatio").joinpath("TestFiles/test_BR.csv")
    )


def configure_file_example(decays: DecayInterface) -> None:
    """Register two channels sharing the same interpolation table."""
    decays.add_decays(
        [
            {"mother": 25, "daughters": [-13, 13]},
            {"mother": 25, "daughters": [22, 22]},
        ],
        CalculationDecayStrategy.FILE_INTERPOLATION,
        {
            "file_path": table_path(),
            "varying_params": ["VeN1", "mN1"],
            "format_type": "csv",
            "BR": False,
        },
    )


def main() -> int:
    """Interpolate the table at an interior scan point."""
    model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
    model.set_leaf_param("VeN1", 1.5)
    model.set_leaf_param("mN1", 1.5)
    decays = DecayInterface(model)
    configure_file_example(decays)
    print("Interpolated widths:", decays.get_brs(25))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
