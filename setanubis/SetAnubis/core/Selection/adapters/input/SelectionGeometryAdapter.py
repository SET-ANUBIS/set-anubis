from SetAnubis.core.Selection.ports.input.ISelectionGeometry import ISelectionGeometry
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple, Callable
import pandas as pd
import math
import numpy as np
import ast


def _as_xyz(vertex: Any) -> Tuple[float, float, float]:
    """
    Normalize 'vertex' to a 3-tuple (x, y, z) of floats.
    Accepts:
      - tuple/list/np.array length >= 3
      - pandas Series with indices [0,1,2] or ['x','y','z']
      - dict with keys 0/1/2 or 'x','y','z'
      - string like '(x, y, z)' or '(x, y, z, t)' -> parsed via ast.literal_eval
    Raises ValueError if cannot parse.
    """
    v = vertex

    # Strings like "(1.0, 2.0, 3.0)" or "[1,2,3,4]"
    if isinstance(v, str):
        v = ast.literal_eval(v)

    # pandas Series
    if isinstance(v, pd.Series):
        if set(['x','y','z']).issubset(v.index):
            return (float(v['x']), float(v['y']), float(v['z']))
        if set([0,1,2]).issubset(v.index):
            return (float(v[0]), float(v[1]), float(v[2]))
        v = v.to_list()

    # dict-like
    if isinstance(v, dict):
        if all(k in v for k in ('x','y','z')):
            return (float(v['x']), float(v['y']), float(v['z']))
        if all(k in v for k in (0,1,2)):
            return (float(v[0]), float(v[1]), float(v[2]))
        # fallthrough to try sequence

    # sequence / np array
    if isinstance(v, (list, tuple, np.ndarray)):
        if len(v) < 3:
            raise ValueError("vertex sequence has less than 3 elements")
        return (float(v[0]), float(v[1]), float(v[2]))

    raise ValueError(f"Unsupported vertex type: {type(vertex)}")

def _get_intersect_fn(geom_proxy) :
    """
    Get the function intersect_stations_simple(θ, φ, (x,y,z), extrema=None)
    from geom_proxy.
    """
    fn = getattr(geom_proxy, "intersect_stations_simple", None)
    if fn is None and hasattr(geom_proxy, "geometry"):
        fn = getattr(geom_proxy.geometry, "intersect_stations_simple", None)
    if fn is None:
        raise AttributeError("No intersect_stations_simple on geometry adapter")
    return fn
    
class SelectionGeometryAdapter(ISelectionGeometry):
    """
    Proxy on the Selection side to the Geometry.
    Can have multiple convention (camelCase, snake_case, getters).
    """

    def __init__(self, geometry_adapter: Any) -> None:
        self._g = geometry_adapter

    def _first_attr(self, obj: Any, names: List[str]):
        for n in names:
            if hasattr(obj, n):
                return getattr(obj, n)
        return None

    def _resolve_attr(self, names: List[str], default: Any = None):
        """
        Looks for the attribut on self._g and self._g.geometry. 
        if callable, we called it.
        """
        cand = self._first_attr(self._g, names)
        if cand is None and hasattr(self._g, "geometry"):
            cand = self._first_attr(self._g.geometry, names)

        if cand is None:
            if default is not None:
                return default
            wanted = "|".join(names)
            raise AttributeError(f"Geometry adapter missing attribute: one of [{wanted}]")

        if callable(cand) and any(n.startswith("get_") for n in names):
            return cand()
        return cand

    def _resolve_callable(self, names: List[str]) -> Callable:
        """
        Return a callable function from self._g or self._g.geometry
        """
        cand = self._first_attr(self._g, names)
        if callable(cand):
            return cand
        if hasattr(self._g, "geometry"):
            cand = self._first_attr(self._g.geometry, names)
            if callable(cand):
                return cand
        wanted = "|".join(names)
        raise AttributeError(f"Geometry adapter missing callable: one of [{wanted}]")

    @property
    def geoMode(self) -> str:
        val = self._resolve_attr(
            ["geoMode", "geo_mode", "mode", "get_geo_mode"],
            default=""
        )
        if callable(val):
            val = val()
        return str(val)

    @property
    def RPCMaxRadius(self) -> float:
        val = self._resolve_attr(
            ["RPCMaxRadius", "rpc_max_radius", "get_rpc_max_radius"],
            default=float("inf")
        )
        if callable(val):
            val = val()
        return float(val)


    def coordsToOrigin(self, x, y, z, origin=[]):
        return self._g.coordsToOrigin(x, y, z, origin)
    

    #Old
    def inCavern(self, x: float, y: float, z: float,
                  max_radius: Optional[float] = None) -> bool:
        return self._g.inCavern(x,y,z,max_radius)
    
    #Old
    def inATLAS(self, x: float, y: float, z: float,
                  max_radius: Optional[float] = None) -> bool:
        return self._g.inATLAS(x,y,z,max_radius)
    
    #Old
    def intersectANUBISstationsSimple(self, theta, phi, d, position, extremaPosition, verbose):
        return self._g.intersectANUBISstationsSimple(theta,phi,d, position, extremaPosition, verbose)

    def reverseCoordsToOrigin(self, x, y, z, origin=[]):
        return self._g.reverseCoordsToOrigin(x,y,z,origin)
    
    @property
    def ANUBIS_RPCs(self) -> str:
        return self._g.ANUBIS_RPCs
    
    def in_cavern(self, decay_vertex_mm, rpc_max_radius):
        try:
            # mm → m
            x_m, y_m, z_m = self._mm_to_m_xyz(decay_vertex_mm)
            # shift legacy: coordsToOrigin(...)
            X, Y, Z = self._coords_to_origin_if_possible(x_m, y_m, z_m)

            fn = getattr(self._g, "inCavern", None)
            if fn is None and hasattr(self._g, "geometry"):
                fn = getattr(self._g.geometry, "inCavern", None)
            if fn is None and hasattr(self._g, "geometry") and hasattr(self._g.geometry, "cavern"):
                fn = getattr(self._g.geometry.cavern, "inCavern", None)

            if fn is None:
                fn = getattr(self._g, "in_cavern", None)
                if fn is None and hasattr(self._g, "geometry"):
                    fn = getattr(self._g.geometry, "in_cavern", None)
            if fn is None:
                raise AttributeError("No cavern check available on geometry adapter")

            mr = "" if (rpc_max_radius is None or math.isinf(rpc_max_radius)) else float(rpc_max_radius)
            try:
                return bool(fn(X, Y, Z, maxRadius=mr))
            except TypeError:
                try:
                    return bool(fn(X, Y, Z, mr))
                except TypeError:
                    return bool(fn(X, Y, Z, max_radius=(None if mr=="" else mr)))
        except Exception:
            return False


    def in_shaft(self, decay_vertex_mm, rpc_max_radius):
        try:
            x_m, y_m, z_m = self._mm_to_m_xyz(decay_vertex_mm)
            X, Y, Z = self._coords_to_origin_if_possible(x_m, y_m, z_m)

            fn = getattr(self._g, "inShaft", None)
            if fn is None and hasattr(self._g, "geometry"):
                fn = getattr(self._g.geometry, "inShaft", None)
            if fn is None and hasattr(self._g, "geometry") and hasattr(self._g.geometry, "cavern"):
                fn = getattr(self._g.geometry.cavern, "inShaft", None)

            if fn is not None:
                includeCone = False
                geoMode = ""
                if hasattr(self._g, "geoMode"): geoMode = getattr(self._g, "geoMode")
                elif hasattr(self._g, "geometry") and hasattr(self._g.geometry, "geoMode"):
                    geoMode = getattr(self._g.geometry, "geoMode")
                includeCone = "cone" in str(geoMode).lower()
                try:
                    return bool(fn(X, Y, Z, includeCavernCone=includeCone))
                except TypeError:
                    return bool(fn(X, Y, Z))

            fn = getattr(self._g, "in_shaft", None)
            if fn is None and hasattr(self._g, "geometry"):
                fn = getattr(self._g.geometry, "in_shaft", None)
            if fn is None:
                raise AttributeError("No shaft check available on geometry adapter")
            try:
                return bool(fn(X, Y, Z, shafts=("PX14", "PX16"), include_cavern_cone=True))
            except TypeError:
                return bool(fn(X, Y, Z))
        except Exception:
            return False


    def in_atlas(self, decay_vertex_mm, strict):
        try:
            x_m, y_m, z_m = self._mm_to_m_xyz(decay_vertex_mm)
            X, Y, Z = self._coords_to_origin_if_possible(x_m, y_m, z_m)

            fn = getattr(self._g, "inATLAS", None)
            if fn is None and hasattr(self._g, "geometry"):
                fn = getattr(self._g.geometry, "inATLAS", None)
            if fn is None and hasattr(self._g, "geometry") and hasattr(self._g.geometry, "cavern"):
                fn = getattr(self._g.geometry.cavern, "inATLAS", None)

            if fn is not None:
                try:
                    return bool(fn(X, Y, Z, bool(strict)))
                except TypeError:
                    return bool(fn(X, Y, Z, trackingOnly=bool(strict)))

            fn = getattr(self._g, "in_atlas", None)
            if fn is None and hasattr(self._g, "geometry"):
                fn = getattr(self._g.geometry, "in_atlas", None)
            if fn is None:
                raise AttributeError("No ATLAS check available on geometry adapter")
            try:
                return bool(fn(X, Y, Z, tracking_only=bool(strict)))
            except TypeError:
                return bool(fn(X, Y, Z, bool(strict)))
        except Exception:
            return False

    def llp_intersections(
        self,
        row: pd.Series,
        decay_vertex_col: str,
        min_p_llp: float,
        plot_trajectory: bool = False,
    ):
        fn = self._resolve_callable([
            "compute_llp_intersections",
            "checkIntersectionsWithANUBIS",
            "check_intersections_with_anubis"
        ])
        # (row, decay_vertex_col, min_p_llp, plot_trajectory)
        return fn(row, decay_vertex_col, min_p_llp, plot_trajectory)

    def decay_hits(
        self,
        llps_df: pd.DataFrame,
        children_df: pd.DataFrame,
        nIntersections: int,
        nTracks: int,
        requireCharge: bool,
        prodVertex: str,
        decayVertex: str,  # Non use here
    ) -> pd.DataFrame:
        """
        - Begining position for start (vertex of children production)
        - conversion mm -> m then coordsToOrigin
        - direction (theta, phi) from (eta, phi) or (px,py,pz)
        - If a children is validated if  >= nIntersections *intersections*
        - Keep LLP with >= nTracks valid childrens
        """
        if llps_df.empty or children_df.empty:
            return llps_df.iloc[0:0]

        ch = children_df
        if requireCharge and "charge" in ch.columns:
            # legacy from paul, -0.555 excluded
            ch = ch[(ch["charge"] != 0) & (ch["charge"] != -0.555)]
        if ch.empty:
            return llps_df.iloc[0:0]

        intersect_fn = _get_intersect_fn(self._g)

        has_eta_phi = ("eta" in ch.columns) and ("phi" in ch.columns)
        has_pxyz    = all(c in ch.columns for c in ("px", "py", "pz"))

        valid_tracks_by_llp: dict[int, int] = {}

        for idx, row in ch.iterrows():
            # parent LLP
            if "LLPindex" not in row:
                continue
            parent_idx = int(row["LLPindex"])

            #beggining position
            pv = row.get(prodVertex, None)
            if pv is None:
                continue

            # mm -> m, then coordsToOrigin (like LLPs)
            try:
                x_m, y_m, z_m = self._mm_to_m_xyz(pv)
                X, Y, Z = self._coords_to_origin_if_possible(x_m, y_m, z_m)
                position = (X, Y, Z)
            except Exception:
                continue

            # direction
            if has_eta_phi:
                try:
                    eta = float(row["eta"])
                    phi = float(row["phi"])
                except Exception:
                    continue
            elif has_pxyz:
                try:
                    px = float(row["px"]); py = float(row["py"]); pz = float(row["pz"])
                    p  = (px*px + py*py + pz*pz) ** 0.5
                    # éviter divisions par 0
                    num = max(p + pz, 1e-300); den = max(p - pz, 1e-300)
                    eta = 0.5 * float(np.log(num / den))
                    phi = float(np.arctan2(py, px))
                except Exception:
                    continue
            else:
                continue
            theta = 2.0 * np.arctan(np.exp(-eta))

            # intersections
            try:
                res = intersect_fn(theta, phi, position, None)
            except TypeError:
                res = intersect_fn(theta, phi, position)

            # normalisation
            points   = getattr(res, "points", None)
            stations = getattr(res, "station_indices", None)
            if points is None and stations is None and isinstance(res, tuple):
                # accept (n, points, stations)
                try:
                    _, points, stations = res
                except Exception:
                    points, stations = [], []

            if points is None:
                points = []
            # --- parité legacy : count the number of intersection, no unique station.
            n_hits = len(points)

            if n_hits >= int(nIntersections):
                valid_tracks_by_llp[parent_idx] = valid_tracks_by_llp.get(parent_idx, 0) + 1

        # LLPs with >= nTracks  valid children
        keep = [i for i, c in valid_tracks_by_llp.items() if c >= int(nTracks)]
        if not keep:
            return llps_df.iloc[0:0]

        return llps_df.loc[llps_df.index.intersection(keep)]
    
    def _coords_to_origin_if_possible(self, x_m: float, y_m: float, z_m: float):
        candidates = [self._g]
        if hasattr(self._g, "geometry"):
            candidates.append(self._g.geometry)
            if hasattr(self._g.geometry, "cavern"):
                candidates.append(self._g.geometry.cavern)
        for obj in candidates:
            cto = getattr(obj, "coordsToOrigin", None)
            if callable(cto):
                return cto(x_m, y_m, z_m)
        return (x_m, y_m, z_m)
    
    def _mm_to_m_xyz(self, decay_vertex_mm):
        x_mm, y_mm, z_mm = _as_xyz(decay_vertex_mm)
        return (x_mm * 1e-3, y_mm * 1e-3, z_mm * 1e-3)