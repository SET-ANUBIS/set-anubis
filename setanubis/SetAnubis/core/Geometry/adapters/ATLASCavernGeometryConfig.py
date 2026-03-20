from dataclasses import dataclass, field
from typing import Literal

@dataclass(frozen=True)
class ATLASCavernGeometryConfig:
    mode: Literal["ceiling", "ceiling_full", "shaft", "shaft+cone"] = "ceiling"
    origin: tuple[float, float, float] | Literal["IP", "cavern"] = "IP"
    rpc_eff: float = 1.0
    n_rpcs_per_layer: int = 1
    rpc_max_radius: float | None = None

    simple_rpc_radii: tuple[float, ...] | None = None
    simple_rpc_thickness: float = 0.06

    shafts: tuple[str, ...] = ("PX14", "PX16")
    include_cavern_cone: bool = True
    shaft_heights: tuple[float, ...] = (0, 1, 18.5, 19.5, 37, 38, 55.5, 56.5)
    shaft_rpc_radius: dict[str, float] = field(
        default_factory=lambda: {"PX14": -1, "PX16": -1}
    )
    shaft_rpc_thickness: float = 0.06
    shaft_clearance: float = 0.25
    shaft_pipe_cutoff: dict[str, float | str] = field(
        default_factory=lambda: {"x": -7.25, "z": ""}
    )

    cache_file: str | None = None
    use_cache: bool = False