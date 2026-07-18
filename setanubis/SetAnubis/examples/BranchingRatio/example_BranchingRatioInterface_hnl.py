"""Combine Python and CSV decay providers through the branching-ratio interface."""

from __future__ import annotations

from SetAnubis.examples._runtime import run_example_entrypoint

from importlib.resources import as_file, files

from SetAnubis import assets_dir
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import (
    CalculationDecayStrategy,
    DecayInterface,
)
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import (
    SetAnubisInterface,
)


def main() -> None:
    """Register Python and CSV providers and evaluate representative channels."""
    model = SetAnubisInterface(str(assets_dir() / "UFO" / "UFO_HNL"))

    # The bundled CSV grid covers mN1 and VeN1 in [1, 2].  Pick an interior
    # point so the example demonstrates interpolation instead of extrapolation.
    model.set_leaf_param("mN1", 1.5)
    model.set_leaf_param("VeN1", 1.5)
    model.set_leaf_param("ZERO", 0.0)

    resources_root = files("SetAnubis.examples.BranchingRatio").joinpath("TestFiles")
    with (
        as_file(resources_root.joinpath("test_BR.py")) as python_script,
        as_file(resources_root.joinpath("test_BR.csv")) as csv_file,
    ):
        decays = DecayInterface(model)
        decays.add_decays(
            [{"mother": 25, "daughters": [5, -5]}],
            CalculationDecayStrategy.PYTHON,
            {"script_path": str(python_script)},
        )
        decays.add_decays(
            [
                {"mother": 25, "daughters": [-13, 13]},
                {"mother": 25, "daughters": [22, 22]},
            ],
            CalculationDecayStrategy.FILE_INTERPOLATION,
            {
                "file_path": str(csv_file),
                "varying_params": ["mN1", "VeN1"],
                "format_type": "csv",
            },
        )

        # Query each provider independently before deriving the normalized BRs.
        gamma_bb_python = decays.get_decay(25, [5, -5])
        gamma_mumu_csv = decays.get_decay(25, [-13, 13])
        gamma_gamma_csv = decays.get_decay(25, [22, 22])
        print(f"[PYTHON] Gamma(H -> b bbar) = {gamma_bb_python}")
        print(f"[CSV] Gamma(H -> mu+ mu-) = {gamma_mumu_csv}")
        print(f"[CSV] Gamma(H -> gamma gamma) = {gamma_gamma_csv}")
        print(f"Total registered width Gamma(H) = {decays.get_decay_tot(25)}")

        for result in decays.get_brs(25):
            print(result)


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
