from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .interfaces import IGeometryBuilder, IGeometry

@dataclass
class GeometryBuildConfig:
    geo_cache_file: str
    origin: Optional[list] = None
    RPCeff: float = 1.0
    nRPCsPerLayer: int = 1
    geometryType: str = ""              # "", "ceiling", "ceiling+singlet", "shaft", "shaft+cone"

class GeometryBuilder:
    def __init__(self, impl: IGeometryBuilder) -> None:
        self._impl = impl

    def build(self) -> IGeometry:
        return self._impl.build()
