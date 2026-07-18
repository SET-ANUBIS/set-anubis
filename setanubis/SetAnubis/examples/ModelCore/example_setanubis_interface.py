"""Inspect and update parameters through the public model-core interface."""

from SetAnubis.examples._runtime import run_example_entrypoint
from setanubis import SetAnubisInterface, ufo_path


def main() -> None:
    """Run a lightweight tour of the HNL UFO parameter interface."""
    # The public interface hides the underlying UFO parser and parameter tree.
    interface = SetAnubisInterface(ufo_path("UFO_HNL"))

    print(interface.get_all_parameters())
    print("-----------------------------------------------------------------")
    print(interface.get_all_particles())
    print(interface.get_particle_mass(23))
    print(interface.get_leaf_parameters())

    print("Setting mass of the Z to 100 GeV")
    interface.set_leaf_param("MZ", 100)
    print(interface.get_particle_mass(23))
    print(interface.get_parameter_expr("MW"))
    print(interface.get_particle_info(25))


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
