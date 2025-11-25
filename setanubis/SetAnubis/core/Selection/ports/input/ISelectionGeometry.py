import pandas as pd
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple

class ISelectionGeometry(Protocol):
    """
      .geoMode: str (p. ex. "ceiling", "shaft", "")
      .RPCMaxRadius: float
      in_cavern(decay_vertex_mm, rpc_max_radius) -> bool
      in_shaft(decay_vertex_mm, rpc_max_radius) -> bool
      in_atlas(decay_vertex_mm, strict) -> bool
      llp_intersections(row, decay_vertex_col, min_p_llp, plot_trajectory) -> (list, list)
      decay_hits(llps_df, children_df, nIntersections, nTracks, requireCharge, prodVertex, decayVertex) -> DataFrame
    """

    @property
    def geoMode(self) -> str: ...
    @property
    def RPCMaxRadius(self) -> float: ...

    def in_cavern(self, decay_vertex_mm: Tuple[float, float, float, float], rpc_max_radius: float) -> bool: ...
    def in_shaft(self, decay_vertex_mm: Tuple[float, float, float, float], rpc_max_radius: float) -> bool: ...
    def in_atlas(self, decay_vertex_mm: Tuple[float, float, float, float], strict: bool) -> bool: ...

    def llp_intersections(
        self,
        row: pd.Series,
        decay_vertex_col: str,
        min_p_llp: float,
        plot_trajectory: bool = False,
    ) -> Tuple[List[Any], List[Any]]: ...

    def decay_hits(
        self,
        llps_df: pd.DataFrame,
        children_df: pd.DataFrame,
        nIntersections: int,
        nTracks: int,
        requireCharge: bool,
        prodVertex: str,
        decayVertex: str,
    ) -> pd.DataFrame: ...