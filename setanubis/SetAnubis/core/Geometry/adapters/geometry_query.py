from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, Optional, List, Tuple
import numpy as np
from ..domain.interfaces import IGeometry
from ..domain.types import Vec3, IntersectionsResult
from SetAnubis.core.Geometry.domain.defineGeometry import ATLASCavern

@dataclass
class CavernQuery(IGeometry):
    cavern: ATLASCavern
    geo_mode: str = ""
    rpc_max_radius: float = float("inf")

    _anubis_dict: dict | None = field(default=None, init=False)

    @property
    def geoMode(self) -> str:
        return self.geo_mode

    @property
    def RPCMaxRadius(self) -> float:
        return float(self.rpc_max_radius)

    def in_cavern(self, x: float, y: float, z: float,
                  max_radius: Optional[float] = None) -> bool:
        mr = "" if (max_radius is None or np.isinf(max_radius)) else float(max_radius)
        
        return bool(self.cavern.inCavern(x, y, z, maxRadius=mr))

    def in_shaft(self, x: float, y: float, z: float,
                 shafts: Iterable[str] = ("PX14",),
                 include_cavern_cone: bool = True) -> bool:
        return bool(self.cavern.inShaft(x, y, z, shafts=list(shafts), includeCavernCone=include_cavern_cone))

    def in_atlas(self, x: float, y: float, z: float,
                 tracking_only: bool = False) -> bool:
        return bool(self.cavern.inATLAS(x, y, z, trackingOnly=bool(tracking_only)))

    
    def coordsToOrigin(self, x, y, z, origin=[]):
        return self.cavern.coordsToOrigin(x,y,z,origin)
    
    def _ensure_rpc_catalog(self) -> None:
        if self._anubis_dict is not None:
            return
        if hasattr(self.cavern, "getANUBISstationsDict"):
            self._anubis_dict = self.cavern.getANUBISstationsDict()
        else:
            self._anubis_dict = getattr(self.cavern, "ANUBIS_RPCs", None)

    def _normalize_intersections_out(
        self, out
    ) -> tuple[int, List[tuple[float,float,float]], List[int]]:
        if isinstance(out, dict):
            n = int(out.get("nIntersections", 0))
            pts = [tuple(map(float, p)) for p in out.get("intersections", [])]
            sts = [int(s) for s in out.get("intersectionStations", [])]
            return n, pts, sts
        if isinstance(out, tuple):
            try:
                n, pts, sts = out
            except ValueError:
                return 0, [], []
            pts = [tuple(map(float, p)) for p in pts]
            stations_norm: List[int] = []
            for s in sts:
                if isinstance(s, (list, tuple)) and len(s) >= 2:
                    stations_norm.append(int(s[0]))
                else:
                    stations_norm.append(int(s))
            return int(n), pts, stations_norm
        return 0, [], []

    def intersectANUBISstationsSimple(self, theta, phi, d, position, extremaPosition, verbose):
        return self.cavern.intersectANUBISstationsSimple(theta,phi,d, position, extremaPosition, verbose)
    
    @property
    def ANUBIS_RPCs(self) -> str:
        return self.cavern.ANUBIS_RPCs

    def reverseCoordsToOrigin(self, x, y, z, origin=[]):
        return self.cavern.reverseCoordsToOrigin(x,y,z,origin)
    
    def intersect_stations_simple(self, theta: float, phi: float,
                                  position: Vec3,
                                  extrema_position: Optional[Vec3] = None) -> IntersectionsResult:
        self._ensure_rpc_catalog()
        d = self._anubis_dict or {}
        ext = [] if extrema_position is None else extrema_position

        if isinstance(d, dict) and {"r", "theta", "phi"} <= set(d.keys()):
            out = self.cavern.intersectANUBISstationsSimple(
                theta, phi, d, position=position, extremaPosition=ext, verbose=False
            )
            _, points, stations = self._normalize_intersections_out(out)
            return IntersectionsResult(points=points, station_indices=stations)

        if isinstance(d, dict) and {"x", "y", "z", "RPCradius"} <= set(d.keys()):
            out = self.cavern.intersectANUBISstationsShaft(
                theta, phi, d, position=position, extremaPosition=ext, verbose=False
            )
            _, points, stations = self._normalize_intersections_out(out)
            return IntersectionsResult(points=points, station_indices=stations)

        if isinstance(d, dict) and {"corners", "midPoint", "plane"} <= set(d.keys()):
            n, points = self.cavern.intersectANUBISstations(
                position[0], position[1], position[2], d, origin=[]
            )
            stations: List[int] = []
            return IntersectionsResult(points=[tuple(p) for p in points], station_indices=stations)

        return IntersectionsResult(points=[], station_indices=[])
