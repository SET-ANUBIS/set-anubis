from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from SetAnubis.HepMCGUI.defineGeometry import ATLASCavern

@dataclass(frozen=True)
class CavernTransform:
    """
    Coordinate transform helper.

    The geometry assumes coordinates relative to the *cavern centre*.
    Many simulations are relative to the IP. ATLASCavern already provides:
      - cavernCentreToIP(x,y,z)
      - IPTocavernCentre(x,y,z)
    """
    cavern: ATLASCavern
    hepmc_positions_are_ip_relative: bool = True

    def to_cavern_centre(self, x_m: float, y_m: float, z_m: float) -> Tuple[float, float, float]:
        if self.hepmc_positions_are_ip_relative:
            return self.cavern.cavernCentreToIP(x_m, y_m, z_m)
        return (x_m, y_m, z_m)
