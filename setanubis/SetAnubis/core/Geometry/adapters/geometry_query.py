"""Adapter exposing the legacy cavern geometry through the modern query API."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from SetAnubis.core.Geometry.domain.defineGeometry import ATLASCavern

from ..domain.interfaces import IGeometry
from ..domain.types import IntersectionsResult, Vec3


@dataclass
class CavernQuery(IGeometry):
    """Translate modern geometry queries to a legacy :class:`ATLASCavern`."""

    cavern: ATLASCavern
    geo_mode: str = ""
    rpc_max_radius: float = float("inf")
    _anubis_dict: dict[str, Any] | None = field(default=None, init=False)

    @property
    def geoMode(self) -> str:
        """Return the configured geometry mode for legacy consumers."""
        return self.geo_mode

    @property
    def RPCMaxRadius(self) -> float:
        """Return the maximum accepted RPC radius."""
        return float(self.rpc_max_radius)

    def in_cavern(
        self,
        x: float,
        y: float,
        z: float,
        max_radius: float | None = None,
    ) -> bool:
        """Return whether a point lies inside the cavern volume."""
        radius = "" if max_radius is None or np.isinf(max_radius) else float(max_radius)
        return bool(self.cavern.inCavern(x, y, z, maxRadius=radius))

    def in_shaft(
        self,
        x: float,
        y: float,
        z: float,
        shafts: Iterable[str] = ("PX14",),
        include_cavern_cone: bool = True,
    ) -> bool:
        """Return whether a point lies inside one of the requested shafts."""
        return bool(
            self.cavern.inShaft(
                x,
                y,
                z,
                shafts=list(shafts),
                includeCavernCone=include_cavern_cone,
            )
        )

    def in_atlas(
        self,
        x: float,
        y: float,
        z: float,
        tracking_only: bool = False,
    ) -> bool:
        """Return whether a point lies inside ATLAS or its tracker."""
        return bool(
            self.cavern.inATLAS(x, y, z, trackingOnly=bool(tracking_only))
        )

    def coordsToOrigin(
        self,
        x: float,
        y: float,
        z: float,
        origin: Sequence[float] | None = None,
    ):
        """Forward legacy coordinate conversion without a mutable default."""
        return self.cavern.coordsToOrigin(x, y, z, [] if origin is None else origin)

    def _ensure_rpc_catalog(self) -> None:
        if self._anubis_dict is not None:
            return
        if hasattr(self.cavern, "getANUBISstationsDict"):
            self._anubis_dict = self.cavern.getANUBISstationsDict()
        else:
            self._anubis_dict = getattr(self.cavern, "ANUBIS_RPCs", None)

    @staticmethod
    def _normalize_intersections_out(
        output: Any,
    ) -> tuple[int, list[tuple[float, float, float]], list[int]]:
        """Normalise legacy dictionary and tuple intersection return values."""
        if isinstance(output, dict):
            count = int(output.get("nIntersections", 0))
            points = [
                tuple(map(float, point)) for point in output.get("intersections", [])
            ]
            stations = [
                int(station) for station in output.get("intersectionStations", [])
            ]
            return count, points, stations
        if isinstance(output, tuple):
            try:
                count, points_raw, stations_raw = output
            except ValueError:
                return 0, [], []
            points = [tuple(map(float, point)) for point in points_raw]
            stations = [
                int(station[0])
                if isinstance(station, (list, tuple)) and len(station) >= 2
                else int(station)
                for station in stations_raw
            ]
            return int(count), points, stations
        return 0, [], []

    def intersectANUBISstationsSimple(
        self,
        theta,
        phi,
        catalog,
        position,
        extremaPosition,
        verbose,
    ):
        """Forward the legacy simple-intersection entry point."""
        return self.cavern.intersectANUBISstationsSimple(
            theta,
            phi,
            catalog,
            position,
            extremaPosition,
            verbose,
        )

    @property
    def ANUBIS_RPCs(self) -> Any:
        """Expose the underlying legacy RPC catalogue."""
        return self.cavern.ANUBIS_RPCs

    def reverseCoordsToOrigin(
        self,
        x: float,
        y: float,
        z: float,
        origin: Sequence[float] | None = None,
    ):
        """Forward the inverse legacy coordinate conversion."""
        return self.cavern.reverseCoordsToOrigin(
            x, y, z, [] if origin is None else origin
        )

    def intersect_stations_simple(
        self,
        theta: float,
        phi: float,
        position: Vec3,
        extrema_position: Vec3 | None = None,
    ) -> IntersectionsResult:
        """Return station intersections for any supported legacy RPC catalogue."""
        self._ensure_rpc_catalog()
        catalog = self._anubis_dict or {}
        extrema = [] if extrema_position is None else extrema_position

        if isinstance(catalog, dict) and {"r", "theta", "phi"} <= catalog.keys():
            output = self.cavern.intersectANUBISstationsSimple(
                theta,
                phi,
                catalog,
                position=position,
                extremaPosition=extrema,
                verbose=False,
            )
            _, points, stations = self._normalize_intersections_out(output)
            return IntersectionsResult(points=points, station_indices=stations)

        if isinstance(catalog, dict) and {
            "x",
            "y",
            "z",
            "RPCradius",
        } <= catalog.keys():
            output = self.cavern.intersectANUBISstationsShaft(
                theta,
                phi,
                catalog,
                position=position,
                extremaPosition=extrema,
                verbose=False,
            )
            _, points, stations = self._normalize_intersections_out(output)
            return IntersectionsResult(points=points, station_indices=stations)

        if isinstance(catalog, dict) and {
            "corners",
            "midPoint",
            "plane",
        } <= catalog.keys():
            _count, points = self.cavern.intersectANUBISstations(
                position[0],
                position[1],
                position[2],
                catalog,
                origin=[],
            )
            return IntersectionsResult(
                points=[tuple(map(float, point)) for point in points],
                station_indices=[],
            )

        return IntersectionsResult(points=[], station_indices=[])
