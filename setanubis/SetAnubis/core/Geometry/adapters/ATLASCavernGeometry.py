
from enum import Enum
from typing import Any, Sequence
import os
import pickle
import numpy as np

from SetAnubis.core.Geometry.ports.ICavernGeometry import ICavernGeometry
from SetAnubis.core.Geometry.domain.GeometryParts import GeometryFrame, GeometryIntersections, GeometryRegion, Vec3
from SetAnubis.core.Geometry.domain.defineGeometry import ATLASCavern
from SetAnubis.core.Geometry.adapters.ATLASCavernGeometryConfig import ATLASCavernGeometryConfig

class ATLASCavernLayout(str, Enum):
    CEILING = "ceiling"
    CEILING_PLUS_SINGLET = "ceiling+singlet"
    FULL_CEILING = "full_ceiling"
    SHAFT = "shaft"
    SHAFT_PLUS_CONE = "shaft+cone"

class ATLASCavernGeometry(ICavernGeometry):
    """
    Concrete geometry facade used by the application.

    `ATLASCavern` remains hidden behind this object. Callers work with:
      - config
      - `inside(...)`
      - `trace(...)`
      - frame conversions
      - RPC lifecycle (`rebuild_rpcs`)

    The goal is to keep Selection, engines and future experiment-specific adapters
    independent from raw `ATLASCavern` internals.
    """

    def __init__(self, cfg: ATLASCavernGeometryConfig) -> None:
        self._cfg = cfg
        self._cavern = self._load_or_create_cavern()
        self._station_catalog_cache: Any = None

        self._apply_runtime_settings()
        self._apply_source_origin()
        self.rebuild_rpcs()

    @classmethod
    def create(cls, cfg: ATLASCavernGeometryConfig) -> "ATLASCavernGeometry":
        return cls(cfg)

    def _load_or_create_cavern(self) -> ATLASCavern:
        if self._cfg.use_cache and self._cfg.cache_file and os.path.isfile(self._cfg.cache_file):
            with open(self._cfg.cache_file, "rb") as pkl:
                cavern = pickle.load(pkl)
                if not isinstance(cavern, ATLASCavern):
                    raise TypeError(
                        f"Cache file does not contain an ATLASCavern: {type(cavern)}"
                    )
                return cavern

        cavern = ATLASCavern()

        if self._cfg.use_cache and self._cfg.cache_file:
            cache_dir = os.path.dirname(self._cfg.cache_file)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
            with open(self._cfg.cache_file, "wb") as pkl:
                pickle.dump(cavern, pkl)

        return cavern
    
    def reconfigure(self, cfg: ATLASCavernGeometryConfig) -> None:
        self._cfg = cfg
        self._apply_runtime_settings()
        self._apply_source_origin()
        self.rebuild_rpcs()
    
    @property
    def mode(self) -> str:
        raw_mode = getattr(self._cavern, "geoMode", None)
        return str(raw_mode) if raw_mode is not None else self._cfg.mode

    @property
    def geoMode(self) -> str:
        return self.mode

    @property
    def layout(self) -> ATLASCavernLayout:
        return ATLASCavernLayout(self._cfg.mode)

    @property
    def rpc_max_radius(self) -> float:
        val = self._cfg.rpc_max_radius
        if val is not None:
            return float(val)
        return float(self._default_rpc_max_radius())

    @property
    def RPCMaxRadius(self) -> float:
        """Compatibility alias kept explicit during the migration."""
        return self.rpc_max_radius

    @property
    def active_rpcs(self) -> Any:
        return getattr(self._cavern, "ANUBIS_RPCs", None)

    
    def to_native_frame(self, position: Sequence[float]) -> Vec3:
        """
        Legacy-compatible convention:
        Selection/source coordinates are converted the same way as the old
        SelectionGeometryAdapter, i.e. by applying the +IP shift.

        """
        x, y, z = _as_vec3(position)

        cto = getattr(self._cavern, "cavernCentreToIP", None)
        if callable(cto):
            out = cto(x, y, z)
        else:
            # fallback: +origin
            out = self._cavern.reverseCoordsToOrigin(x, y, z)

        return float(out[0]), float(out[1]), float(out[2])


    def from_native_frame(self, position: Sequence[float]) -> Vec3:
        """
        Inverse of the legacy-compatible SOURCE -> NATIVE transform.
        """
        x, y, z = _as_vec3(position)

        itc = getattr(self._cavern, "IPTocavernCentre", None)
        if callable(itc):
            out = itc(x, y, z)
        else:
            # fallback: -origin
            out = self._cavern.coordsToOrigin(x, y, z)

        return float(out[0]), float(out[1]), float(out[2])

    def inside(
        self,
        region: GeometryRegion,
        position: Sequence[float],
        *,
        frame: GeometryFrame = GeometryFrame.SOURCE,
        max_radius: float | None = None,
        tracking_only: bool = False,
    ) -> bool:
        x, y, z = self._normalize_position(position, frame=frame)

        if region is GeometryRegion.FIDUCIAL:
            mr = self.rpc_max_radius if max_radius is None else float(max_radius)
            mr_arg = "" if np.isinf(mr) else float(mr)
            return bool(self._cavern.inCavern(x, y, z, maxRadius=mr_arg))

        if region is GeometryRegion.AUXILIARY:
            return bool(
                self._cavern.inShaft(
                    x,
                    y,
                    z,
                    shafts=list(self._cfg.shafts),
                    includeCavernCone=self._resolved_include_cavern_cone(),
                )
            )

        if region is GeometryRegion.DETECTOR:
            return bool(self._cavern.inATLAS(x, y, z, trackingOnly=bool(tracking_only)))

        raise ValueError(f"Unsupported region: {region}")
    
    def trace(
        self,
        theta: float,
        phi: float,
        position: Sequence[float],
        extrema_position: Sequence[float] | None = None,
        *,
        frame: GeometryFrame = GeometryFrame.SOURCE,
    ) -> GeometryIntersections:
        start = self._normalize_position(position, frame=frame)
        stop = None
        if extrema_position is not None:
            stop = self._normalize_position(extrema_position, frame=frame)

        catalog = self.get_station_catalog()
        ext = [] if stop is None else stop

        if isinstance(catalog, dict) and {"r", "theta", "phi"} <= set(catalog.keys()):
            out = self._cavern.intersectANUBISstationsSimple(
                theta,
                phi,
                catalog,
                position=start,
                extremaPosition=ext,
                verbose=False,
            )
            _, points, stations = self._normalize_intersections_out(out)
            return GeometryIntersections(points=points, station_indices=stations)

        if isinstance(catalog, dict) and {"x", "y", "z", "RPCradius"} <= set(catalog.keys()):
            out = self._cavern.intersectANUBISstationsShaft(
                theta,
                phi,
                catalog,
                position=start,
                extremaPosition=ext,
                verbose=False,
            )
            _, points, stations = self._normalize_intersections_out(out)
            return GeometryIntersections(points=points, station_indices=stations)

        if isinstance(catalog, dict) and {"corners", "midPoint", "plane"} <= set(catalog.keys()):
            _, points = self._cavern.intersectANUBISstations(
                start[0],
                start[1],
                start[2],
                catalog,
                origin=[],
            )
            pts = [tuple(map(float, p)) for p in points]
            return GeometryIntersections(points=pts, station_indices=[])

        return GeometryIntersections(points=[], station_indices=[])
    
    def rebuild_rpcs(self) -> Any:
        self._station_catalog_cache = None

        if self.layout is ATLASCavernLayout.CEILING:
            radii = self._resolved_simple_radii(default_three_layers=True)
            return self._cavern.createSimpleRPCs(
                list(radii),
                RPCthickness=float(self._cfg.simple_rpc_thickness),
            )

        if self.layout is ATLASCavernLayout.SHAFT:
            return self._cavern.createShaftRPCs(
                list(self._cfg.shaft_heights),
                RPCradius=dict(self._cfg.shaft_rpc_radius),
                RPCthickness=float(self._cfg.shaft_rpc_thickness),
                clearance=float(self._cfg.shaft_clearance),
                pipeCutoff=dict(self._cfg.shaft_pipe_cutoff),
                shafts=list(self._cfg.shafts),
                includeCone=False,
            )

        if self.layout is ATLASCavernLayout.SHAFT_PLUS_CONE:
            return self._cavern.createShaftRPCs(
                list(self._cfg.shaft_heights),
                RPCradius=dict(self._cfg.shaft_rpc_radius),
                RPCthickness=float(self._cfg.shaft_rpc_thickness),
                clearance=float(self._cfg.shaft_clearance),
                pipeCutoff=dict(self._cfg.shaft_pipe_cutoff),
                shafts=list(self._cfg.shafts),
                includeCone=True,
            )

        if self.layout is ATLASCavernLayout.FULL_CEILING:
            raise NotImplementedError(
                "mode='ceiling_full' is declared in the config but the required "
                "full ceiling parameters are not present in ATLASCavernGeometryConfig."
            )

        raise ValueError(f"Unsupported layout: {self.layout}")
    
    def get_station_catalog(self) -> Any:
        if self._station_catalog_cache is not None:
            return self._station_catalog_cache

        if hasattr(self._cavern, "getANUBISstationsDict"):
            self._station_catalog_cache = self._cavern.getANUBISstationsDict()
            return self._station_catalog_cache

        catalog = getattr(self._cavern, "ANUBIS_RPCs", None)
        if catalog is None:
            raise RuntimeError(
                "No active RPC layout on the cavern. "
                "Call rebuild_rpcs() or enable auto_create_rpc_layout in the config."
            )

        self._station_catalog_cache = catalog
        return self._station_catalog_cache

    def _apply_runtime_settings(self) -> None:
        self._cavern.RPCeff = float(self._cfg.rpc_eff)
        self._cavern.nRPCsPerLayer = int(self._cfg.n_rpcs_per_layer)
        self._cavern.RPCMaxRadius = float(self.rpc_max_radius)

    def _apply_source_origin(self) -> None:
        origin = self._cfg.origin

        if isinstance(origin, str):
            key = origin.strip().lower()
            if key == "ip":
                self._cavern.posOrigin = [
                    float(self._cavern.IP["x"]),
                    float(self._cavern.IP["y"]),
                    float(self._cavern.IP["z"]),
                ]
                return

            if key in {"cavern", "native", "cavern_centre", "cavern_center"}:
                self._cavern.posOrigin = [0.0, 0.0, 0.0]
                return

            raise ValueError(
                f"Unsupported origin='{self._cfg.origin}'. "
                "Use 'IP', 'cavern', or an explicit (x, y, z) tuple."
            )

        x, y, z = _as_vec3(origin)
        self._cavern.posOrigin = [x, y, z]

    def _normalize_position(
        self,
        position: Sequence[float],
        *,
        frame: GeometryFrame,
    ) -> Vec3:
        x, y, z = _as_vec3(position)
        if frame is GeometryFrame.NATIVE:
            return x, y, z
        return self.to_native_frame((x, y, z))

    def _resolved_include_cavern_cone(self) -> bool:
        if self.layout is ATLASCavernLayout.SHAFT_PLUS_CONE:
            return True
        return bool(self._cfg.include_cavern_cone)
    
    def _resolved_simple_radii(self, *, default_three_layers: bool) -> tuple[float, ...]:
        if self._cfg.simple_rpc_radii is not None:
            return tuple(float(v) for v in self._cfg.simple_rpc_radii)

        if default_three_layers:
            return (
                float(self._cavern.archRadius - 0.2),
                float(self._cavern.archRadius - 0.6),
                float(self._cavern.archRadius - 1.2),
            )

        return (
            float(self._cavern.archRadius - 0.2),
            float(self._cavern.archRadius - 1.2),
        )

    def _resolved_full_layer_radii(self) -> tuple[float, ...]:
        if self._cfg.full_layer_radii is not None:
            return tuple(float(v) for v in self._cfg.full_layer_radii)

        return (
            float(self._cavern.archRadius),
            float(self._cavern.archRadius - 0.40),
            float(self._cavern.archRadius - 1.00),
        )

    def _default_rpc_max_radius(self) -> float:
        return float(self._cavern.archRadius - 1.2 - 0.5)

    def _build_full_ceiling_rpcs(self) -> list[dict[str, Any]]:
        all_rpcs: list[dict[str, Any]] = []

        for layer_id, radius in enumerate(self._resolved_full_layer_radii()):
            layer_rpcs = self._cavern.ANUBIS_RPC_positions(
                RPCx=float(self._cfg.full_rpc_x),
                RPCy=float(self._cfg.full_rpc_y),
                RPCz=float(self._cfg.full_rpc_z),
                overlapAngleXY=float(self._cfg.full_overlap_angle_xy),
                overlapZ=float(self._cfg.full_overlap_z),
                layerRadius=float(radius),
                ID=int(layer_id),
            )
            all_rpcs.extend(layer_rpcs)

        self._cavern.ANUBIS_RPCs = all_rpcs
        self._cavern.geoMode = "fullCeiling"
        return all_rpcs
    
    @staticmethod
    def _normalize_intersections_out(
        out: Any,
    ) -> tuple[int, list[Vec3], list[int]]:
        if isinstance(out, dict):
            n = int(out.get("nIntersections", 0))
            pts = [tuple(map(float, p)) for p in out.get("intersections", [])]
            sts = [int(s) for s in out.get("intersectionStations", [])]
            return n, pts, sts

        if isinstance(out, tuple):
            try:
                n, pts, sts = out
            except ValueError:
                return 0, [], []

            pts = [tuple(map(float, p)) for p in pts]
            stations_norm: list[int] = []
            for station in sts:
                if isinstance(station, (list, tuple)) and len(station) >= 1:
                    stations_norm.append(int(station[0]))
                else:
                    stations_norm.append(int(station))
            return int(n), pts, stations_norm

        return 0, [], []


def _as_vec3(value: Sequence[float]) -> Vec3:
    if isinstance(value, np.ndarray):
        arr = value.tolist()
    else:
        arr = list(value)

    if len(arr) < 3:
        raise ValueError(f"Expected at least 3 coordinates, got {len(arr)}")

    return float(arr[0]), float(arr[1]), float(arr[2])
