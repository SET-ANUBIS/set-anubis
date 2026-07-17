"""Geometry contract consumed by the event-selection pipeline."""

from typing import Any, List, Protocol, Tuple

import pandas as pd


class ISelectionGeometry(Protocol):
    """Expose containment and hit calculations required by selection cuts."""

    @property
    def geoMode(self) -> str:
        """Return the active detector geometry mode."""
        ...

    @property
    def RPCMaxRadius(self) -> float:
        """Return the maximum RPC radius used for containment checks."""
        ...

    def in_cavern(
        self,
        decay_vertex_mm: Tuple[float, float, float, float],
        rpc_max_radius: float,
    ) -> bool:
        """Return whether a decay vertex lies inside the cavern volume."""
        ...

    def in_shaft(
        self,
        decay_vertex_mm: Tuple[float, float, float, float],
        rpc_max_radius: float,
    ) -> bool:
        """Return whether a decay vertex lies inside the shaft volume."""
        ...

    def in_atlas(
        self,
        decay_vertex_mm: Tuple[float, float, float, float],
        strict: bool,
    ) -> bool:
        """Return whether a decay vertex lies inside the ATLAS veto volume."""
        ...

    def llp_intersections(
        self,
        row: pd.Series,
        decay_vertex_col: str,
        min_p_llp: float,
        plot_trajectory: bool = False,
    ) -> Tuple[List[Any], List[Any]]:
        """Calculate detector intersections for one LLP candidate."""
        ...

    def decay_hits(
        self,
        llps_df: pd.DataFrame,
        children_df: pd.DataFrame,
        nIntersections: int,
        nTracks: int,
        requireCharge: bool,
        prodVertex: str,
        decayVertex: str,
    ) -> pd.DataFrame:
        """Return LLP candidates whose charged daughters satisfy hit cuts."""
        ...
