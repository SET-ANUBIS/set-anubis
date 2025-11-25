from __future__ import annotations
from typing import Any, Tuple, Dict, List, Optional
import numpy as np
import pandas as pd

from ..domain.interfaces import IGeometry
from ..domain.utils import eta_to_theta, extract_xyz
from ..domain.types import IntersectionsResult

def _mm_to_m_tuple(pos):
    x, y, z = pos
    return (float(x) * 1e-3, float(y) * 1e-3, float(z) * 1e-3)

def _coords_to_origin_if_possible(geometry, x_m, y_m, z_m):
    for obj in (geometry, getattr(geometry, "geometry", None), getattr(getattr(geometry, "geometry", None), "cavern", None)):
        if obj is None:
            continue
        fn = getattr(obj, "coordsToOrigin", None)
        if callable(fn):
            try:
                return fn(x_m, y_m, z_m)
            except Exception:
                pass
    return (x_m, y_m, z_m)
    
class GeometrySelectionAdapter:

    def __init__(self, geometry: IGeometry) -> None:
        self.geometry = geometry

    def inCavern(self, x: float, y: float, z: float,
                  max_radius: Optional[float] = None) -> bool:
        return self.geometry.in_cavern(x,y,z,max_radius)
    
    def inATLAS(self, x: float, y: float, z: float,
                  max_radius: Optional[float] = None) -> bool:
        return self.geometry.in_atlas(x,y,z,max_radius)
    
    def coordsToOrigin(self, x, y, z, origin=[]):
        return self.geometry.coordsToOrigin(x,y,z,origin)
    
    @property
    def ANUBIS_RPCs(self) -> str:
        return self.geometry.ANUBIS_RPCs
    
    def reverseCoordsToOrigin(self, x, y, z, origin=[]):
        return self.geometry.reverseCoordsToOrigin(x,y,z,origin)

    def intersectANUBISstationsSimple(self, theta, phi, d, position, extremaPosition, verbose):
        return self.geometry.intersectANUBISstationsSimple(theta,phi,d, position, extremaPosition, verbose)

    def checkInCavern(self, row: pd.Series, rpc_max_radius: float, decay_vertex_col: str) -> bool:
        x, y, z = extract_xyz(row[decay_vertex_col])
        mr = rpc_max_radius if np.isfinite(rpc_max_radius) else None
        return self.geometry.in_cavern(x, y, z, max_radius=mr)

    def checkInShaft(self, row: pd.Series, rpc_max_radius: float, decay_vertex_col: str) -> bool:
        x, y, z = extract_xyz(row[decay_vertex_col])
        return self.geometry.in_shaft(x, y, z, shafts=("PX14", "PX16"), include_cavern_cone=True)

    def checkInATLAS(self, row: pd.Series, tracking_only: bool, decay_vertex_col: str) -> bool:
        x, y, z = extract_xyz(row[decay_vertex_col])
        return self.geometry.in_atlas(x, y, z, tracking_only=bool(tracking_only))

    def checkIntersectionsWithANUBIS(
        self,
        row: pd.Series,
        decay_vertex_col: str,
        min_p_llp: float,
        plot_trajectory: bool = False,
    ) -> Tuple[List[Tuple[float, float, float]], List[int]]:

        p = None
        if "p" in row:
            try:
                p = float(row["p"])
            except Exception:
                p = None
        if p is None and all(k in row for k in ("px", "py", "pz")):
            try:
                p = float((row["px"]**2 + row["py"]**2 + row["pz"]**2)**0.5)
            except Exception:
                p = None
        if p is not None and p < float(min_p_llp):
            return ([], [])

        eta = float(row["eta"])
        phi = float(row["phi"])
        theta = 2.0 * np.arctan(np.exp(-eta))

        pos_mm = extract_xyz(row[decay_vertex_col])
        if pos_mm is None:
            return ([], [])
        x_m, y_m, z_m = _mm_to_m_tuple(pos_mm)
        X, Y, Z = _coords_to_origin_if_possible(self.geometry, x_m, y_m, z_m)
        position = (X, Y, Z)

        try:
            res = self.geometry.intersect_stations_simple(theta, phi, position, None)
        except TypeError:
            res = self.geometry.intersect_stations_simple(theta, phi, position)

        points = getattr(res, "points", None)
        stations = getattr(res, "station_indices", None)
        if points is None and stations is None and isinstance(res, tuple):
            try:
                _, points, stations = res
            except Exception:
                points, stations = [], []

        if points is None:
            points = []
        if stations is None:
            stations = []

        points = [tuple(map(float, p)) for p in points]
        try:
            stations = [int(s[1]) if isinstance(s, (list, tuple)) and len(s) >= 2 else int(s) for s in stations]
        except Exception:
            stations = [int(s) for s in stations if isinstance(s, (int, np.integer))]

        return (points, stations)