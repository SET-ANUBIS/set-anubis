from __future__ import annotations

import ast
import math
from typing import Any

import numpy as np
import pandas as pd
from collections import defaultdict

from SetAnubis.core.Selection.ports.input.ISelectionGeometry import ISelectionGeometry
from SetAnubis.core.Geometry.adapters.ATLASCavernGeometry import (
    ICavernGeometry,
    GeometryFrame,
    GeometryIntersections,
    GeometryRegion,
)

from dataclasses import dataclass

@dataclass(frozen=True)
class _DecayTrackSegment:
    llp_index: int
    child_index: Any
    parent_ref: int | None
    start_m: tuple[float, float, float]
    stop_m: tuple[float, float, float] | None
    theta: float
    phi: float
    charge: float | None
    pdg_id: int | None
    points: list[tuple[float, float, float]]
    station_indices: list[int]

    @property
    def station_score(self) -> int:
        if self.station_indices:
            return len(set(int(s) for s in self.station_indices))
        return len(self.points)


@dataclass(frozen=True)
class _DecayTrackCandidate:
    llp_index: int
    segment_indices: tuple[Any, ...]
    points: list[tuple[float, float, float]]
    station_indices: list[int]

    @property
    def station_score(self) -> int:
        if self.station_indices:
            return len(set(int(s) for s in self.station_indices))
        return len(self.points)

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

def _ordered_unique_ints(values: list[int]) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for v in values:
        iv = int(v)
        if iv not in seen:
            seen.add(iv)
            out.append(iv)
    return out

def _distance_m(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(
        (float(a[0]) - float(b[0])) ** 2
        + (float(a[1]) - float(b[1])) ** 2
        + (float(a[2]) - float(b[2])) ** 2
    )


def _maybe_int_from_row(row: pd.Series, candidates: tuple[str, ...]) -> int | None:
    for col in candidates:
        if col in row.index and pd.notna(row[col]):
            try:
                return int(row[col])
            except Exception:
                pass
    return None

def _maybe_float_from_row(row: pd.Series, candidates: tuple[str, ...]) -> float | None:
    for col in candidates:
        if col in row.index and pd.notna(row[col]):
            try:
                return float(row[col])
            except Exception:
                pass
    return None

class ATLASCavernSelectionGeometryAdapter(ISelectionGeometry):
    """
    Concrete Selection-side adapter for ICavernGeometry / ATLASCavernGeometry.

    This class is Selection-specific:
      - it consumes LLP/children dataframes
      - it converts vertices from mm to m
      - it derives theta/phi from eta/phi or px/py/pz
      - it uses the generic Geometry regions and tracing API
    """

    _VERTEX_LINK_TOLERANCE_M = 1.0e-4  # 0.1 mm
    
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

    def filter_decay_hits_old(
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
        - build bounded charged segments using prodVertex -> decayVertex
        - merge successive charged segments into reconstructed track candidates
        - count reconstructed track candidates, not raw child rows
        - store details for plotting/debugging in the returned dataframe
        """
        if llps_df.empty or children_df.empty:
            return llps_df.iloc[0:0].copy()

        ch = children_df.copy()

        if requireCharge and ("charge" in ch.columns):
            charge = pd.to_numeric(ch["charge"], errors="coerce")
            ch = ch[charge.notna() & (charge != 0)]

        if ch.empty:
            return llps_df.iloc[0:0].copy()

        segments_by_llp = self._build_segments_by_llp(
            ch,
            prodVertex=prodVertex,
            decayVertex=decayVertex,
        )

        segment_payloads: dict[int, list[dict[str, Any]]] = {}
        candidate_payloads: dict[int, list[dict[str, Any]]] = {}
        passing_payloads: dict[int, list[dict[str, Any]]] = {}
        passing_count: dict[int, int] = {}

        for llp_idx, segments in segments_by_llp.items():
            candidates = self._build_track_candidates_for_llp(segments)
            passing = [
                cand
                for cand in candidates
                if cand.station_score >= int(nIntersections)
            ]

            segment_payloads[llp_idx] = [self._segment_to_payload(seg) for seg in segments]
            candidate_payloads[llp_idx] = [self._candidate_to_payload(c) for c in candidates]
            passing_payloads[llp_idx] = [self._candidate_to_payload(c) for c in passing]
            passing_count[llp_idx] = len(passing)

        annotated = llps_df.copy()

        annotated["decayTrackSegments"] = [
            segment_payloads.get(int(idx), []) for idx in annotated.index
        ]
        annotated["decayTrackCandidates"] = [
            candidate_payloads.get(int(idx), []) for idx in annotated.index
        ]
        annotated["decayTrackPassing"] = [
            passing_payloads.get(int(idx), []) for idx in annotated.index
        ]
        annotated["nDecayTrackCandidates"] = [
            len(candidate_payloads.get(int(idx), [])) for idx in annotated.index
        ]
        annotated["nDecayTrackPassing"] = [
            passing_count.get(int(idx), 0) for idx in annotated.index
        ]

        keep_idx = [
            idx
            for idx in annotated.index
            if passing_count.get(int(idx), 0) >= int(nTracks)
        ]

        if not keep_idx:
            return annotated.iloc[0:0].copy()

        return annotated.loc[annotated.index.intersection(keep_idx)].copy()

    def _build_segments_by_llp(
        self,
        children_df: pd.DataFrame,
        *,
        prodVertex: str,
        decayVertex: str,
    ) -> dict[int, list[_DecayTrackSegment]]:
        out: dict[int, list[_DecayTrackSegment]] = defaultdict(list)
        has_decay_vertex = decayVertex in children_df.columns

        for child_idx, row in children_df.iterrows():
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
                result = self._geometry.trace(
                    theta,
                    phi,
                    start_m,
                    extrema_position=stop_m,   # important: bounded segment
                    frame=GeometryFrame.SOURCE,
                )
            except Exception:
                continue

            segment = _DecayTrackSegment(
                llp_index=parent_idx,
                child_index=child_idx,
                parent_ref=_maybe_int_from_row(
                    row,
                    (
                        "parentIndex",
                        "motherIndex",
                        "motherParticleIndex",
                        "parentParticleIndex",
                    ),
                ),
                start_m=start_m,
                stop_m=stop_m,
                theta=theta,
                phi=phi,
                charge=_maybe_float_from_row(row, ("charge",)),
                pdg_id=_maybe_int_from_row(row, ("pdgId", "pdgID", "pid", "PDGID")),
                points=[tuple(map(float, p)) for p in result.points],
                station_indices=[int(s) for s in result.station_indices],
            )
            out[parent_idx].append(segment)

        return out

    def _build_track_candidates_for_llp(
        self,
        segments: list[_DecayTrackSegment],
    ) -> list[_DecayTrackCandidate]:
        if not segments:
            return []

        by_id = {seg.child_index: seg for seg in segments}
        successors: dict[Any, list[Any]] = {seg.child_index: [] for seg in segments}
        incoming: dict[Any, set[Any]] = {seg.child_index: set() for seg in segments}

        # explicit parent references if present
        for child in segments:
            if child.parent_ref is None:
                continue
            if child.parent_ref not in by_id:
                continue

            parent = by_id[child.parent_ref]
            if self._is_segment_successor(parent, child):
                successors[parent.child_index].append(child.child_index)
                incoming[child.child_index].add(parent.child_index)

        # fallback by vertex continuity for rows without an incoming edge
        for parent in segments:
            if parent.stop_m is None:
                continue

            for child in segments:
                if parent.child_index == child.child_index:
                    continue

                if incoming[child.child_index]:
                    continue

                if self._is_segment_successor(parent, child):
                    successors[parent.child_index].append(child.child_index)
                    incoming[child.child_index].add(parent.child_index)

        roots = [seg.child_index for seg in segments if not incoming[seg.child_index]]
        if not roots:
            roots = [seg.child_index for seg in segments]

        terminal_paths: list[tuple[Any, ...]] = []

        def _dfs(node_id: Any, path: list[Any]) -> None:
            nxt = successors.get(node_id, [])
            if not nxt:
                terminal_paths.append(tuple(path + [node_id]))
                return
            for child_id in nxt:
                if child_id in path:
                    continue
                _dfs(child_id, path + [node_id])

        for root in roots:
            _dfs(root, [])

        if not terminal_paths:
            terminal_paths = [(seg.child_index,) for seg in segments]

        terminal_paths = list(dict.fromkeys(terminal_paths))

        candidates: list[_DecayTrackCandidate] = []
        for path in terminal_paths:
            ordered_segments = [by_id[idx] for idx in path]

            all_points: list[tuple[float, float, float]] = []
            all_stations: list[int] = []

            for seg in ordered_segments:
                all_points.extend(seg.points)
                all_stations.extend(seg.station_indices)

            candidates.append(
                _DecayTrackCandidate(
                    llp_index=ordered_segments[0].llp_index,
                    segment_indices=tuple(path),
                    points=all_points,
                    station_indices=_ordered_unique_ints(all_stations),
                )
            )

        return candidates

    def _is_segment_successor(
        self,
        parent: _DecayTrackSegment,
        child: _DecayTrackSegment,
    ) -> bool:
        if parent.llp_index != child.llp_index:
            return False

        if parent.stop_m is None:
            return False

        if _distance_m(parent.stop_m, child.start_m) > self._VERTEX_LINK_TOLERANCE_M:
            return False

        # If both charges are known, enforce same sign to avoid accidental merges.
        if (parent.charge is not None) and (child.charge is not None):
            if parent.charge == 0 or child.charge == 0:
                return False
            if math.copysign(1.0, parent.charge) != math.copysign(1.0, child.charge):
                return False

        return True

    @staticmethod
    def _segment_to_payload(seg: _DecayTrackSegment) -> dict[str, Any]:
        return {
            "child_index": seg.child_index,
            "parent_ref": seg.parent_ref,
            "start_m": seg.start_m,
            "stop_m": seg.stop_m,
            "charge": seg.charge,
            "pdg_id": seg.pdg_id,
            "theta": seg.theta,
            "phi": seg.phi,
            "points": seg.points,
            "station_indices": seg.station_indices,
            "station_score": seg.station_score,
        }

    @staticmethod
    def _candidate_to_payload(cand: _DecayTrackCandidate) -> dict[str, Any]:
        return {
            "segment_indices": list(cand.segment_indices),
            "points": cand.points,
            "station_indices": cand.station_indices,
            "station_score": cand.station_score,
        }
        
    def _infer_default_decay_region(self) -> GeometryRegion:
        mode = str(self._geometry.mode).lower()

        if "shaft" in mode:
            return GeometryRegion.AUXILIARY

        return GeometryRegion.FIDUCIAL