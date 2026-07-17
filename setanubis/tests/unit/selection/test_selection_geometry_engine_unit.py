"""Tests for the canonical selection engine and geometry adapter."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from SetAnubis.core.Geometry.domain.GeometryParts import (
    GeometryFrame,
    GeometryIntersections,
    GeometryRegion,
)
from SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter import (
    SelectionGeometryAdapter,
)
from SetAnubis.core.Selection.domain.SelectionEngine import (
    RunConfig,
    SelectionConfig,
    SelectionEngine,
)


class FakeCavernGeometry:
    """Small geometry backend implementing the production geometry protocol."""

    mode = "ceiling"
    rpc_max_radius = 9.5

    def __init__(self) -> None:
        self.inside_calls: list[tuple[GeometryRegion, tuple[float, float, float]]] = []

    def to_native_frame(self, position):
        return tuple(position)

    def from_native_frame(self, position):
        return tuple(position)

    def inside(
        self,
        region,
        position,
        *,
        frame=GeometryFrame.SOURCE,
        max_radius=None,
        tracking_only=False,
    ):
        self.inside_calls.append((region, tuple(position)))
        return region is not GeometryRegion.DETECTOR

    def trace(
        self,
        theta,
        phi,
        position,
        extrema_position=None,
        *,
        frame=GeometryFrame.SOURCE,
    ):
        return GeometryIntersections(
            points=[(1.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
            station_indices=[0, 1],
        )

    def rebuild_rpcs(self):
        return None

    def get_station_catalog(self):
        return []


def test_selection_geometry_adapter_supplies_current_engine_contract():
    backend = FakeCavernGeometry()
    geometry = SelectionGeometryAdapter(backend)

    assert geometry.default_decay_region is GeometryRegion.FIDUCIAL
    assert geometry.default_fiducial_radius == pytest.approx(9.5)
    assert geometry.inside(GeometryRegion.FIDUCIAL, (1000.0, 0.0, 0.0))
    assert backend.inside_calls[-1] == (
        GeometryRegion.FIDUCIAL,
        (1.0, 0.0, 0.0),
    )


def test_selection_engine_uses_geometry_region_contract_without_legacy_attributes():
    geometry = SelectionGeometryAdapter(FakeCavernGeometry())
    selection = SelectionConfig(geometry=geometry)
    dataframe = pd.DataFrame(
        {
            "decayVertex": [(1000.0, 0.0, 0.0)],
            "weight": [2.0],
        },
        index=[7],
    )

    result = SelectionEngine()._select_in_decay_region(
        dataframe,
        selection,
        RunConfig(reweightLifetime=False, plotTrajectory=False),
    )

    assert result["dataframe"].index.tolist() == [7]
    assert result["cutFlow"] == {
        "nLLP_InCavern": 1,
        "nLLP_InCavern_weighted": 2.0,
    }


def test_incomplete_legacy_geometry_adapter_is_rejected_immediately():
    class LegacyGeometry:
        geoMode = "ceiling"
        RPCMaxRadius = 10.0

    with pytest.raises(TypeError, match="ICavernGeometry-compatible"):
        SelectionGeometryAdapter(LegacyGeometry())


def test_only_one_selection_engine_implementation_is_kept():
    domain = Path(__file__).resolve().parents[3] / "SetAnubis/core/Selection/domain"
    ports = Path(__file__).resolve().parents[3] / "SetAnubis/core/Selection/ports/input"
    adapters = (
        Path(__file__).resolve().parents[3]
        / "SetAnubis/core/Selection/adapters/input"
    )

    assert (domain / "SelectionEngine.py").is_file()
    assert not (domain / "SelectionEnginev2.py").exists()
    assert (ports / "ISelectionGeometry.py").is_file()
    assert not (ports / "ISelectionGeometryv2.py").exists()
    assert (adapters / "SelectionGeometryAdapter.py").is_file()
    assert not (adapters / "ATLASCavernSelectionGeometryAdapter.py").exists()
