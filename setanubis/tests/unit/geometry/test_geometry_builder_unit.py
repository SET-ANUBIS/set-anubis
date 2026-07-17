"""Unit tests for the cached cavern geometry builder."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from SetAnubis.core.Geometry.adapters import geometry_builder
from SetAnubis.core.Geometry.domain.builder import GeometryBuildConfig


@dataclass
class _FakeCavern:
    """Small pickle-safe stand-in for the legacy cavern implementation."""

    archRadius: float = 10.0
    IP: dict[str, float] = field(
        default_factory=lambda: {"x": 1.0, "y": 2.0, "z": 3.0}
    )
    calls: list[tuple] = field(default_factory=list)

    def createSimpleRPCs(self, radii, *, RPCthickness):
        self.calls.append(("simple", list(radii), RPCthickness))

    def createShaftRPCs(self, positions, *, RPCthickness, includeCone):
        self.calls.append(
            ("shaft", list(positions), RPCthickness, bool(includeCone))
        )


def _config(cache_path, **overrides):
    values = {
        "geo_cache_file": str(cache_path),
        "origin": None,
        "RPCeff": 0.9,
        "nRPCsPerLayer": 3,
        "geometryType": "ceiling",
    }
    values.update(overrides)
    return GeometryBuildConfig(**values)


def test_builder_constructs_caches_and_reloads_cavern(monkeypatch, tmp_path):
    monkeypatch.setattr(geometry_builder, "ATLASCavern", _FakeCavern)
    cache = tmp_path / "nested" / "geometry.pkl"

    first = geometry_builder.CavernGeometryBuilder(_config(cache)).build()
    assert cache.is_file()
    assert first.cavern.calls == [("simple", [9.8, 8.8], 0.06)]
    assert first.cavern.posOrigin == [1.0, 2.0, 3.0]
    assert first.cavern.RPCeff == pytest.approx(0.9)
    assert first.cavern.nRPCsPerLayer == 3
    assert first.RPCMaxRadius == pytest.approx(8.3)

    second = geometry_builder.CavernGeometryBuilder(
        _config(cache, RPCeff=0.75, nRPCsPerLayer=2)
    ).build()
    assert second.cavern.calls == first.cavern.calls
    assert second.cavern.RPCeff == pytest.approx(0.75)
    assert second.cavern.nRPCsPerLayer == 2


@pytest.mark.parametrize(
    ("geometry_type", "expected"),
    [
        ("ceiling+singlet", ("simple", [9.8, 9.4, 8.8], 0.06)),
        ("shaft", ("shaft", [0, 1, 18.5, 19.5, 37, 38, 55.5, 56.5], 0.06, False)),
        ("shaft+cone", ("shaft", [0, 1, 18.5, 19.5, 37, 38, 55.5, 56.5], 0.06, True)),
    ],
)
def test_builder_supports_all_documented_geometry_modes(
    monkeypatch, tmp_path, geometry_type, expected
):
    monkeypatch.setattr(geometry_builder, "ATLASCavern", _FakeCavern)
    query = geometry_builder.CavernGeometryBuilder(
        _config(
            tmp_path / f"{geometry_type}.pkl",
            geometryType=geometry_type,
            origin=[4.0, 5.0, 6.0],
        )
    ).build()
    assert query.cavern.calls == [expected]
    assert query.cavern.posOrigin == [4.0, 5.0, 6.0]


def test_builder_rejects_unknown_geometry_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(geometry_builder, "ATLASCavern", _FakeCavern)
    builder = geometry_builder.CavernGeometryBuilder(
        _config(tmp_path / "invalid.pkl", geometryType="not-a-mode")
    )
    with pytest.raises(ValueError, match="Unknown geometry type"):
        builder.build()
