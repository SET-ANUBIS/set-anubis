"""Protocol implemented by ANUBIS cavern geometry backends."""

from typing import Any, Protocol, Sequence, runtime_checkable

from SetAnubis.core.Geometry.domain.GeometryParts import (
    GeometryFrame,
    GeometryIntersections,
    GeometryRegion,
    Vec3,
)


@runtime_checkable
class ICavernGeometry(Protocol):
    """Coordinate conversion, containment and trajectory-tracing contract."""

    @property
    def mode(self) -> str:
        """Return the active geometry layout name."""
        ...

    @property
    def rpc_max_radius(self) -> float:
        """Return the maximum radial extent used for RPC acceptance."""
        ...

    def to_native_frame(self, position: Sequence[float]) -> Vec3:
        """Convert a position from the source frame to the native frame."""
        ...

    def from_native_frame(self, position: Sequence[float]) -> Vec3:
        """Convert a position from the native frame to the source frame."""
        ...

    def inside(
        self,
        region: GeometryRegion,
        position: Sequence[float],
        *,
        frame: GeometryFrame = GeometryFrame.SOURCE,
        max_radius: float | None = None,
        tracking_only: bool = False,
    ) -> bool:
        """Return whether ``position`` lies inside ``region``."""
        ...

    def trace(
        self,
        theta: float,
        phi: float,
        position: Sequence[float],
        extrema_position: Sequence[float] | None = None,
        *,
        frame: GeometryFrame = GeometryFrame.SOURCE,
    ) -> GeometryIntersections:
        """Trace a trajectory and return its detector intersections."""
        ...

    def rebuild_rpcs(self) -> Any:
        """Rebuild cached RPC geometry and return the backend result."""
        ...

    def get_station_catalog(self) -> Any:
        """Return the detector-station catalogue used by the backend."""
        ...
