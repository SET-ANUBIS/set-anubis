from __future__ import annotations
from typing import Protocol, Iterable, Optional, Tuple, List
from .types import Vec3, IntersectionsResult

class IGeometry(Protocol):
    @property
    def geoMode(self) -> str: ...
    @property
    def RPCMaxRadius(self) -> float: ...

    def in_cavern(self, x: float, y: float, z: float,
                  max_radius: Optional[float] = None) -> bool: ...
    def in_shaft(self, x: float, y: float, z: float,
                 shafts: Iterable[str] = ("PX14",),
                 include_cavern_cone: bool = True) -> bool: ...
    def in_atlas(self, x: float, y: float, z: float,
                 tracking_only: bool = False) -> bool: ...

    def intersect_stations_simple(self, theta: float, phi: float,
                                  position: Vec3,
                                  extrema_position: Optional[Vec3] = None) -> IntersectionsResult: ...

class IGeometryBuilder(Protocol):
    def build(self) -> "IGeometry": ...

class IGeometryPlotter(Protocol):
    def plot(self, geometry: IGeometry, *, show: bool = True, savepath: Optional[str] = None) -> None: ...
