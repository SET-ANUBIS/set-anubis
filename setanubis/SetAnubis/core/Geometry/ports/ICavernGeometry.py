from SetAnubis.core.Geometry.domain.GeometryParts import GeometryFrame, GeometryRegion, GeometryIntersections, Vec3
from typing import Any, Protocol, Sequence, runtime_checkable

@runtime_checkable
class ICavernGeometry(Protocol):
    @property
    def mode(self) -> str:
        ...

    @property
    def rpc_max_radius(self) -> float:
        ...

    def to_native_frame(self, position: Sequence[float]) -> Vec3:
        ...

    def from_native_frame(self, position: Sequence[float]) -> Vec3:
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
        ...

    def rebuild_rpcs(self) -> Any:
        ...

    def get_station_catalog(self) -> Any:
        ...