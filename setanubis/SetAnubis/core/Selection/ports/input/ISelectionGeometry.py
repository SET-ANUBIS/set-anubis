from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import pandas as pd

from SetAnubis.core.Geometry.adapters.ATLASCavernGeometry import (
    GeometryIntersections,
    GeometryRegion,
)


@runtime_checkable
class ISelectionGeometry(Protocol):
    """
    Selection-side contract, independent from a concrete experiment geometry.

    The Selection layer should reason in terms of:
      - regions (fiducial / auxiliary / detector / ...)
      - containment checks
      - intersections / tracing
      - filtering LLPs based on decay-product hits

    It should NOT know about:
      - ATLAS-specific names such as cavern / shaft / ATLAS
      - raw ATLASCavern internals
      - guessed method names on adapters
    """

    @property
    def default_decay_region(self) -> GeometryRegion:
        """
        Region used by default for the LLP decay acceptance step.
        Example:
          - ceiling-like setup -> FIDUCIAL
          - shaft-like setup   -> AUXILIARY
        """
        ...

    @property
    def default_fiducial_radius(self) -> float:
        """
        Default radius constraint used when Selection wants to restrict the
        fiducial volume, e.g. for ANUBIS acceptance.
        """
        ...

    def inside(
        self,
        region: GeometryRegion,
        decay_vertex_mm: Any,
        *,
        max_radius: float | None = None,
        tracking_only: bool = False,
    ) -> bool:
        """
        Selection-facing containment check.
        Input vertex is in mm, because that is what the Selection dataframes use.
        """
        ...

    def intersections(
        self,
        row: pd.Series,
        decay_vertex_col: str,
        min_p_llp: float,
        plot_trajectory: bool = False,
    ) -> GeometryIntersections:
        """
        Compute detector intersections for a given LLP row.
        """
        ...

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
        Keep LLPs that satisfy the requested decay-product hit requirements.
        """
        ...