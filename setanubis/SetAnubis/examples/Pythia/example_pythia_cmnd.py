"""Build a Pythia CMND card for HNL production and decay without running Pythia."""

from __future__ import annotations

from importlib.resources import as_file, files

from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import (
    CalculationDecayStrategy,
    DecayInterface,
)
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import (
    SetAnubisInterface,
)
from SetAnubis.core.Pythia.adapters.input.PythiaCMNDInterface import (
    PythiaCMNDInterface,
)
from SetAnubis.core.Pythia.infrastructure.enums import HardProductionQCDList
from SetAnubis.resources import ufo_path


def build_cmnd() -> str:
    """Return an HNL CMND card assembled from packaged calculation scripts."""
    model = SetAnubisInterface(ufo_path("UFO_HNL"))
    model.set_leaf_param("mN1", 1.0)

    resources_root = files("SetAnubis.examples.Pythia").joinpath("TestFiles")
    with (
        as_file(resources_root.joinpath("HNL_eq.py")) as decay_script,
        as_file(resources_root.joinpath("production_eq.py")) as production_script,
        as_file(resources_root.joinpath("sm_particles_changes.yaml")) as particle_yaml,
    ):
        decays = DecayInterface(model)
        decays.add_decays(
            [
                {"mother": 9900012, "daughters": [12, -12, 12]},
                {"mother": 9900012, "daughters": [-11, 11, 12]},
                {"mother": 9900012, "daughters": [11, -11, 14]},
                {"mother": 9900012, "daughters": [11, -11, 16]},
                {"mother": 9900012, "daughters": [11, -13, 14]},
                {"mother": 9900012, "daughters": [13, -11, 12]},
            ],
            CalculationDecayStrategy.PYTHON,
            {"script_path": str(decay_script)},
        )
        decays.add_decays(
            [
                {"mother": 4132, "daughters": [9900012, -11, 3312]},
                {"mother": 4132, "daughters": [9900012, -13, 3312]},
                {"mother": 421, "daughters": [9900012, -11, -321]},
                {"mother": 421, "daughters": [9900012, -11, -323]},
                {"mother": 421, "daughters": [9900012, -13, -321]},
            ],
            CalculationDecayStrategy.PYTHON,
            {"script_path": str(production_script)},
        )

        command = PythiaCMNDInterface(model, decays)
        command.change_sm_particles([4132], particle_yaml)
        command.add_new_particles([9900012])
        command.add_hard_production(HardProductionQCDList.HARDQCD_HARD_C_CBAR)
        command.add_hard_production(HardProductionQCDList.HARDQCD_HARDB_B_BAR)
        command.add_decay_to_bsm_particles(9900012)
        command.add_decay_from_bsm_particles(9900012)
        return command.serialize()


def main() -> None:
    """Build and print the CMND card without starting the Pythia runtime."""
    print("CMND generated:\n")
    print(build_cmnd())


if __name__ == "__main__":
    main()
