from __future__ import annotations
import numpy as np
from typing import Tuple

def eta_to_theta(eta: float) -> float:
    # θ = 2 arctan(e^{-η})
    return 2.0 * np.arctan(np.exp(-float(eta)))

def extract_xyz(fourvec_like) -> Tuple[float, float, float]:
    # (x,y,z) or (x,y,z,t)
    x, y, z = float(fourvec_like[0]), float(fourvec_like[1]), float(fourvec_like[2])
    return x, y, z
