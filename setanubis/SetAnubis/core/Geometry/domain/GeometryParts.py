from enum import Enum
from dataclasses import dataclass

Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class GeometryIntersections:
    points: list[Vec3]
    station_indices: list[int]

    @property
    def count(self) -> int:
        return len(self.points)


class GeometryRegion(str, Enum):
    """
    Generic regions that higher-level adapters can target.

    - FIDUCIAL: experiment acceptance / allowed decay region.
    - AUXILIARY: service volume attached to the main cavern (ATLAS shafts here).
    - DETECTOR: detector envelope (ATLAS here, CMS tomorrow, etc.).
    """

    FIDUCIAL = "fiducial"
    AUXILIARY = "auxiliary"
    DETECTOR = "detector"


class GeometryFrame(str, Enum):
    """
    - SOURCE: frame used by the external caller / simulation input.
    - NATIVE: frame used internally by the backend geometry object.
    """

    SOURCE = "source"
    NATIVE = "native"