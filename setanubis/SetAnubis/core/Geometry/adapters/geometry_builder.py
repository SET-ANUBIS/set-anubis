from __future__ import annotations
import os, pickle
from dataclasses import dataclass
from typing import Optional, Any
from ..domain.interfaces import IGeometry, IGeometryBuilder
from ..domain.builder import GeometryBuildConfig
from ..domain.types import IntersectionsResult, Vec3
from ..domain import interfaces as I
from ..domain import types as T
from ..domain import builder as B
from ..domain import interfaces
from ..domain import types
from ..domain import builder
from ..domain import interfaces
from ..domain import types
from ..domain import builder
from ..domain import interfaces
from ..domain import types
from ..domain import builder
from ..domain import interfaces
from ..domain import types
from ..domain import builder

from SetAnubis.core.Geometry.domain.defineGeometry import ATLASCavern
from .geometry_query import CavernQuery

@dataclass
class CavernGeometryBuilder(IGeometryBuilder):
    cfg: B.GeometryBuildConfig

    def _create_or_load_cavern(self) -> ATLASCavern:
        path = self.cfg.geo_cache_file
        if os.path.isfile(path):
            with open(path, "rb") as pkl:
                cavern = pickle.load(pkl)
        else:
            cavern = ATLASCavern()
            gt = (self.cfg.geometryType or "").lower()
            if gt in ("", "ceiling"):
                cavern.createSimpleRPCs([cavern.archRadius-0.2, cavern.archRadius-1.2], RPCthickness=0.06)
            elif gt == "ceiling+singlet":
                cavern.createSimpleRPCs([cavern.archRadius-0.2, cavern.archRadius-0.6, cavern.archRadius-1.2], RPCthickness=0.06)
            elif gt == "shaft":
                cavern.createShaftRPCs([0,1,18.5,19.5,37,38,55.5,56.5], RPCthickness=0.06, includeCone=False)
            elif gt == "shaft+cone":
                cavern.createShaftRPCs([0,1,18.5,19.5,37,38,55.5,56.5], RPCthickness=0.06, includeCone=True)
            else:
                raise ValueError(f"Unknown geometry type: {self.cfg.geometryType}")

            cavern.RPCMaxRadius = cavern.archRadius - 1.2 - 0.5

            origin = self.cfg.origin
            if origin == "IP" or not origin:
                cavern.posOrigin = [cavern.IP["x"], cavern.IP["y"], cavern.IP["z"]]
            else:
                cavern.posOrigin = origin

            with open(path, "wb") as pkl:
                pickle.dump(cavern, pkl)

        cavern.RPCeff = float(self.cfg.RPCeff)
        cavern.nRPCsPerLayer = int(self.cfg.nRPCsPerLayer)
        return cavern

    def build(self) -> IGeometry:
        cav = self._create_or_load_cavern()
        return CavernQuery(
            cavern=cav,
            geo_mode=self.cfg.geometryType or "",
            rpc_max_radius=getattr(cav, "RPCMaxRadius", float("inf")),
        )
