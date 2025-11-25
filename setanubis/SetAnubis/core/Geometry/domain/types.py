from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence, Tuple, List

Vec3 = Tuple[float, float, float]
FourVec = Tuple[float, float, float, float]

@dataclass(frozen=True)
class IntersectionsResult:
    points: List[Vec3]
    station_indices: List[int]
