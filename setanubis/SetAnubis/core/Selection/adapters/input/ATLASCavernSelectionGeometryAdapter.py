from __future__ import annotations

import ast
import math
from typing import Any

import numpy as np
import pandas as pd

from SetAnubis.core.Selection.ports.input.ISelectionGeometry import ISelectionGeometry
from SetAnubis.core.Geometry.adapters.ATLASCavernGeometry import (
    ICavernGeometry,
    GeometryFrame,
    GeometryIntersections,
    GeometryRegion,
)


def _as_xyz(vertex: Any) -> tuple[float, float, float]:
    """
    Normalize a vertex-like object to (x, y, z).
    Accepted:
      - tuple/list/np.ndarray
      - pandas Series with x,y,z or 0,1,2
      - dict with x,y,z or 0,1,2
      - string representation like '(x, y, z)' or '[x, y, z, t]'
    """
    value = vertex

    if isinstance(value, str):
        value = ast.literal_eval(value)

    if isinstance(value, pd.Series):
        if {"x", "y", "z"}.issubset(value.index):
            return float(value["x"]), float(value["y"]), float(value["z"])
        if {0, 1, 2}.issubset(value.index):
            return float(value[0]), float(value[1]), float(value[2])
        value = value.to_list()

    if isinstance(value, dict):
        if all(k in value for k in ("x", "y", "z")):
            return float(value["x"]), float(value["y"]), float(value["z"])
        if all(k in value for k in (0, 1, 2)):
            return float(value[0]), float(value[1]), float(value[2])

    if isinstance(value, (list, tuple, np.ndarray)):
        if len(value) < 3:
            raise ValueError("vertex sequence has less than 3 elements")
        return float(value[0]), float(value[1]), float(value[2])

    raise ValueError(f"Unsupported vertex type: {type(vertex)}")


def _mm_to_m_xyz(vertex_mm: Any) -> tuple[float, float, float]:
    x_mm, y_mm, z_mm = _as_xyz(vertex_mm)
    return x_mm * 1.0e-3, y_mm * 1.0e-3, z_mm * 1.0e-3


def _eta_phi_from_row(row: pd.Series) -> tuple[float, float]:
    """
    Prefer eta/phi if present, otherwise derive them from px/py/pz.
    """
    if ("eta" in row.index) and ("phi" in row.index):
        return float(row["eta"]), float(row["phi"])

    if all(k in row.index for k in ("px", "py", "pz")):
        px = float(row["px"])
        py = float(row["py"])
        pz = float(row["pz"])

        p = math.sqrt(px * px + py * py + pz * pz)
        if p <= 0.0:
            raise ValueError("Cannot derive eta/phi from zero momentum")

        num = max(p + pz, 1.0e-300)
        den = max(p - pz, 1.0e-300)
        eta = 0.5 * math.log(num / den)
        phi = math.atan2(py, px)
        return eta, phi

    raise ValueError("Row does not contain eta/phi nor px/py/pz")


def _theta_from_eta(eta: float) -> float:
    return 2.0 * math.atan(math.exp(-float(eta)))


class ATLASCavernSelectionGeometryAdapter(ISelectionGeometry):
    """
    Concrete Selection-side adapter for ICavernGeometry / ATLASCavernGeometry.

    This class is Selection-specific:
      - it consumes LLP/children dataframes
      - it converts vertices from mm to m
      - it derives theta/phi from eta/phi or px/py/pz
      - it uses the generic Geometry regions and tracing API
    """

    def __init__(
        self,
        geometry: ICavernGeometry,
        *,
        default_decay_region: GeometryRegion | None = None,
    ) -> None:
        if not isinstance(geometry, ICavernGeometry):
            raise TypeError(
                "ATLASCavernSelectionGeometryAdapter expects an ICavernGeometry-compatible object"
            )

        self._geometry = geometry
        self._default_decay_region = (
            default_decay_region if default_decay_region is not None
            else self._infer_default_decay_region()
        )

    @property
    def default_decay_region(self) -> GeometryRegion:
        return self._default_decay_region

    @property
    def default_fiducial_radius(self) -> float:
        return float(self._geometry.rpc_max_radius)

    def inside(
        self,
        region: GeometryRegion,
        decay_vertex_mm: Any,
        *,
        max_radius: float | None = None,
        tracking_only: bool = False,
    ) -> bool:
        position_m = _mm_to_m_xyz(decay_vertex_mm)

        return bool(
            self._geometry.inside(
                region,
                position_m,
                frame=GeometryFrame.SOURCE,
                max_radius=max_radius,
                tracking_only=bool(tracking_only),
            )
        )

    def intersections(
        self,
        row: pd.Series,
        decay_vertex_col: str,
        min_p_llp: float,
        plot_trajectory: bool = False,
    ) -> GeometryIntersections:
        if decay_vertex_col not in row.index:
            return GeometryIntersections(points=[], station_indices=[])

        if ("p" in row.index) and pd.notna(row["p"]) and (float(row["p"]) < float(min_p_llp)):
            return GeometryIntersections(points=[], station_indices=[])

        try:
            eta, phi = _eta_phi_from_row(row)
        except Exception:
            return GeometryIntersections(points=[], station_indices=[])

        theta = _theta_from_eta(eta)
        position_m = _mm_to_m_xyz(row[decay_vertex_col])

        return self._geometry.trace(
            theta,
            phi,
            position_m,
            extrema_position=None,
            frame=GeometryFrame.SOURCE,
        )

    def filter_decay_hits(
        self,
        llps_df: pd.DataFrame,
        children_df: pd.DataFrame,
        nIntersections: int,
        nTracks: int,
        requireCharge: bool,
        prodVertex: str,
        decayVertex: str,
    ) -> pd.DataFrame:
        """
        Keep LLPs that have at least `nTracks` decay products with
        at least `nIntersections` geometry intersections.
        """
        if llps_df.empty or children_df.empty:
            return llps_df.iloc[0:0]

        ch = children_df.copy()

        if requireCharge and ("charge" in ch.columns):
            charge = pd.to_numeric(ch["charge"], errors="coerce")
            ch = ch[charge.notna() & (charge != 0)]

        if ch.empty:
            return llps_df.iloc[0:0]

        valid_tracks_by_llp: dict[int, int] = {}
        has_decay_vertex = decayVertex in ch.columns

        for _, row in ch.iterrows():
            if "LLPindex" not in row.index or pd.isna(row["LLPindex"]):
                continue

            parent_idx = int(row["LLPindex"])

            if prodVertex not in row.index or pd.isna(row[prodVertex]):
                continue

            try:
                start_m = _mm_to_m_xyz(row[prodVertex])
            except Exception:
                continue

            stop_m = None
            if has_decay_vertex and pd.notna(row[decayVertex]):
                try:
                    stop_m = _mm_to_m_xyz(row[decayVertex])
                except Exception:
                    stop_m = None

            try:
                eta, phi = _eta_phi_from_row(row)
            except Exception:
                continue

            theta = _theta_from_eta(eta)

            try:
                #TODO : paul is this normal ?
                # result = self._geometry.trace(
                #     theta,
                #     phi,
                #     start_m,
                #     extrema_position=stop_m,
                #     frame=GeometryFrame.SOURCE,
                # )
                result = self._geometry.trace(
                    theta,
                    phi,
                    start_m,
                    extrema_position=None,
                    frame=GeometryFrame.SOURCE,
                )
            except Exception:
                continue

            if len(result.points) >= int(nIntersections):
                valid_tracks_by_llp[parent_idx] = valid_tracks_by_llp.get(parent_idx, 0) + 1

        keep_llp_indices = [
            llp_idx
            for llp_idx, n_valid_tracks in valid_tracks_by_llp.items()
            if n_valid_tracks >= int(nTracks)
        ]

        if not keep_llp_indices:
            return llps_df.iloc[0:0]

        return llps_df.loc[llps_df.index.intersection(keep_llp_indices)]

    def _infer_default_decay_region(self) -> GeometryRegion:
        mode = str(self._geometry.mode).lower()

        if "shaft" in mode:
            return GeometryRegion.AUXILIARY

        return GeometryRegion.FIDUCIAL