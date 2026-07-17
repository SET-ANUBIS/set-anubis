"""Build or restore the legacy cavern geometry behind the query interface."""

from __future__ import annotations

import os
import pickle
from dataclasses import dataclass

from SetAnubis.core.Geometry.domain.defineGeometry import ATLASCavern

from ..domain import builder as builder_domain
from ..domain.interfaces import IGeometry, IGeometryBuilder
from .geometry_query import CavernQuery


@dataclass
class CavernGeometryBuilder(IGeometryBuilder):
    """Create an ``ATLASCavern`` and expose it through ``CavernQuery``."""

    cfg: builder_domain.GeometryBuildConfig

    def _create_or_load_cavern(self) -> ATLASCavern:
        """Load the configured cache or construct and cache a new cavern."""
        path = self.cfg.geo_cache_file
        if os.path.isfile(path):
            with open(path, "rb") as stream:
                cavern = pickle.load(stream)
        else:
            cavern = ATLASCavern()
            geometry_type = (self.cfg.geometryType or "").lower()
            if geometry_type in ("", "ceiling"):
                cavern.createSimpleRPCs(
                    [cavern.archRadius - 0.2, cavern.archRadius - 1.2],
                    RPCthickness=0.06,
                )
            elif geometry_type == "ceiling+singlet":
                cavern.createSimpleRPCs(
                    [
                        cavern.archRadius - 0.2,
                        cavern.archRadius - 0.6,
                        cavern.archRadius - 1.2,
                    ],
                    RPCthickness=0.06,
                )
            elif geometry_type == "shaft":
                cavern.createShaftRPCs(
                    [0, 1, 18.5, 19.5, 37, 38, 55.5, 56.5],
                    RPCthickness=0.06,
                    includeCone=False,
                )
            elif geometry_type == "shaft+cone":
                cavern.createShaftRPCs(
                    [0, 1, 18.5, 19.5, 37, 38, 55.5, 56.5],
                    RPCthickness=0.06,
                    includeCone=True,
                )
            else:
                raise ValueError(f"Unknown geometry type: {self.cfg.geometryType}")

            cavern.RPCMaxRadius = cavern.archRadius - 1.2 - 0.5
            cavern.posOrigin = (
                [cavern.IP["x"], cavern.IP["y"], cavern.IP["z"]]
                if self.cfg.origin in (None, "IP")
                else self.cfg.origin
            )

            cache_parent = os.path.dirname(os.path.abspath(path))
            os.makedirs(cache_parent, exist_ok=True)
            with open(path, "wb") as stream:
                pickle.dump(cavern, stream)

        cavern.RPCeff = float(self.cfg.RPCeff)
        cavern.nRPCsPerLayer = int(self.cfg.nRPCsPerLayer)
        return cavern

    def build(self) -> IGeometry:
        """Return a query façade for the configured cavern geometry."""
        cavern = self._create_or_load_cavern()
        return CavernQuery(
            cavern=cavern,
            geo_mode=self.cfg.geometryType or "",
            rpc_max_radius=getattr(cavern, "RPCMaxRadius", float("inf")),
        )
