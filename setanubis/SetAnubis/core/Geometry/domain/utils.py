"""Small numerical helpers shared by geometry adapters."""

from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np


def eta_to_theta(eta: float) -> float:
    """Convert pseudorapidity ``eta`` to the polar angle ``theta`` in radians."""

    return float(2.0 * np.arctan(np.exp(-float(eta))))


def extract_xyz(fourvec_like: Sequence[float]) -> Tuple[float, float, float]:
    """Extract the first three Cartesian coordinates from a vector-like value."""

    x, y, z = (
        float(fourvec_like[0]),
        float(fourvec_like[1]),
        float(fourvec_like[2]),
    )
    return x, y, z
