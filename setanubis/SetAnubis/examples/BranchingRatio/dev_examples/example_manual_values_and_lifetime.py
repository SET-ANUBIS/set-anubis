"""Register manual widths or branching ratios and derive a particle lifetime."""

from __future__ import annotations

from SetAnubis import DecayInterface, SetAnubisInterface, Unit, ufo_path


def configure_manual_example(decays: DecayInterface) -> None:
    """Register two toy partial widths for a Higgs-like mother particle."""
    # Manual values are useful for validation, external calculations, or scans
    # where the observable has already been computed elsewhere.
    decays.set_decay(25, [-13, 13], 1.0e-3)
    decays.set_decay(25, [22, 22], 5.0e-3)


def main() -> int:
    """Run the manual-width example with the packaged HNL UFO model."""
    model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
    decays = DecayInterface(model)
    configure_manual_example(decays)

    print("Total width [GeV]:", decays.get_decay_tot(25))
    print("Branching ratios:", decays.get_brs(25))
    print("Lifetime [s]:", decays.calculate_lifetime(25, Unit.S))

    # A direct BR can also be registered when no total width is available.
    decays.set_decay(9900012, [11, -11, 12], 0.25, is_br=True)
    print("Direct HNL branching ratio:", decays.get_br(9900012, [11, -11, 12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
