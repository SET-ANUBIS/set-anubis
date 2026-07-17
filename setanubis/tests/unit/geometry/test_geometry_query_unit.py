"""Unit tests for the legacy cavern query adapter."""

from __future__ import annotations

from SetAnubis.core.Geometry.adapters.geometry_query import CavernQuery


class _Cavern:
    def __init__(self, catalog=None):
        self.catalog = catalog
        self.ANUBIS_RPCs = catalog
        self.calls = []

    def getANUBISstationsDict(self):
        return self.catalog

    def inCavern(self, x, y, z, **kwargs):
        self.calls.append(("cavern", x, y, z, kwargs))
        return x > 0

    def inShaft(self, x, y, z, **kwargs):
        self.calls.append(("shaft", x, y, z, kwargs))
        return y > 0

    def inATLAS(self, x, y, z, **kwargs):
        self.calls.append(("atlas", x, y, z, kwargs))
        return z > 0

    def coordsToOrigin(self, x, y, z, origin):
        self.calls.append(("coords", origin))
        return x + 1, y + 1, z + 1

    def reverseCoordsToOrigin(self, x, y, z, origin):
        self.calls.append(("reverse", origin))
        return x - 1, y - 1, z - 1

    def intersectANUBISstationsSimple(self, *args, **kwargs):
        self.calls.append(("simple", args, kwargs))
        return {
            "nIntersections": 1,
            "intersections": [[1, 2, 3]],
            "intersectionStations": [4],
        }

    def intersectANUBISstationsShaft(self, *args, **kwargs):
        self.calls.append(("shaft-intersection", args, kwargs))
        return 1, [[4, 5, 6]], [[7, "unused"]]

    def intersectANUBISstations(self, *args, **kwargs):
        self.calls.append(("plane", args, kwargs))
        return 1, [[7, 8, 9]]


def test_point_queries_properties_and_coordinate_forwarding():
    cavern = _Cavern({"r": [], "theta": [], "phi": []})
    query = CavernQuery(cavern, geo_mode="ceiling", rpc_max_radius=12.5)

    assert query.geoMode == "ceiling"
    assert query.RPCMaxRadius == 12.5
    assert query.in_cavern(1, 0, 0)
    assert not query.in_cavern(-1, 0, 0, max_radius=float("inf"))
    assert query.in_shaft(0, 1, 0, shafts=("PX14", "PX16"))
    assert query.in_atlas(0, 0, 1, tracking_only=True)
    assert query.coordsToOrigin(1, 2, 3) == (2, 3, 4)
    assert query.reverseCoordsToOrigin(1, 2, 3, origin=(0, 0, 0)) == (0, 1, 2)
    assert query.ANUBIS_RPCs == cavern.catalog
    assert cavern.calls[0][-1] == {"maxRadius": ""}
    assert cavern.calls[2][-1]["shafts"] == ["PX14", "PX16"]


def test_intersection_output_normalisation_handles_supported_shapes():
    assert CavernQuery._normalize_intersections_out(
        {
            "nIntersections": 1,
            "intersections": [[1, 2, 3]],
            "intersectionStations": [4],
        }
    ) == (1, [(1.0, 2.0, 3.0)], [4])
    assert CavernQuery._normalize_intersections_out(
        (1, [[1, 2, 3]], [[5, "ignored"]])
    ) == (1, [(1.0, 2.0, 3.0)], [5])
    assert CavernQuery._normalize_intersections_out((1, 2)) == (0, [], [])
    assert CavernQuery._normalize_intersections_out(None) == (0, [], [])


def test_intersections_support_simple_shaft_plane_and_empty_catalogues():
    simple = CavernQuery(_Cavern({"r": [], "theta": [], "phi": []}))
    result = simple.intersect_stations_simple(0.1, 0.2, (0, 0, 0))
    assert result.points == [(1.0, 2.0, 3.0)]
    assert result.station_indices == [4]

    shaft = CavernQuery(
        _Cavern({"x": [], "y": [], "z": [], "RPCradius": []})
    )
    result = shaft.intersect_stations_simple(
        0.1, 0.2, (0, 0, 0), extrema_position=(1, 1, 1)
    )
    assert result.points == [(4.0, 5.0, 6.0)]
    assert result.station_indices == [7]

    plane = CavernQuery(
        _Cavern({"corners": [], "midPoint": [], "plane": []})
    )
    result = plane.intersect_stations_simple(0.1, 0.2, (1, 2, 3))
    assert result.points == [(7.0, 8.0, 9.0)]
    assert result.station_indices == []

    empty = CavernQuery(_Cavern({}))
    result = empty.intersect_stations_simple(0.1, 0.2, (0, 0, 0))
    assert result.points == [] and result.station_indices == []


def test_legacy_simple_intersection_method_forwards_positional_arguments():
    cavern = _Cavern({})
    query = CavernQuery(cavern)
    output = query.intersectANUBISstationsSimple(
        0.1, 0.2, {"r": []}, (0, 0, 0), [], False
    )
    assert output["nIntersections"] == 1
