from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

from SetAnubis.HepMCGUI.defineGeometry import ATLASCavern


def _norm_phi(phi: np.ndarray) -> np.ndarray:
    out = np.mod(phi, 2 * np.pi)
    out[out < 0] += 2 * np.pi
    return out


@dataclass(frozen=True)
class RegionClassifier:
    """
    Vectorized region tests for decay/production vertices.

    Single responsibility: classify points into geometry regions.
    """
    cavern: ATLASCavern

    def in_atlas(self, x: np.ndarray, y: np.ndarray, z: np.ndarray, tracking_only: bool = False) -> np.ndarray:
        ipx, ipy = float(self.cavern.IP["x"]), float(self.cavern.IP["y"])
        r = np.hypot(x - ipx, y - ipy)
        r_target = float(self.cavern.radiusATLAStracking if tracking_only else self.cavern.radiusATLAS)
        z0, z1 = float(self.cavern.ATLAS_Z[0]), float(self.cavern.ATLAS_Z[1])
        return (r < r_target) & (z > z0) & (z < z1)

    def in_cavern(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        c = self.cavern
        x0, x1 = float(c.CavernX[0]), float(c.CavernX[1])
        z0, z1 = float(c.CavernZ[0]), float(c.CavernZ[1])
        y_min = float(c.CavernY[0])
        cocx, cocy = float(c.centreOfCurvature["x"]), float(c.centreOfCurvature["y"])
        R = float(c.archRadius)

        within_x = (x > x0) & (x < x1)
        within_z = (z > z0) & (z < z1)
        # ceiling y(x) = cocy + sqrt(R^2 - (x-cocx)^2) for valid domain
        dx2 = (x - cocx) ** 2
        inside_sqrt = (R**2 - dx2)
        valid = inside_sqrt > 0
        ceiling = np.full_like(x, np.nan, dtype=float)
        ceiling[valid] = cocy + np.sqrt(inside_sqrt[valid])

        within_y = (y > y_min) & (y < ceiling)
        return within_x & within_y & within_z & valid

    def in_anubis_ceiling_simple(self, x: np.ndarray, y: np.ndarray, z: np.ndarray, simple_rpcs: Dict[str, Any]) -> np.ndarray:
        """
        "Point lies within one of the simple RPC annuli arcs" (proxy for 'in ANUBIS ceiling station').
        """
        c = self.cavern
        cocx, cocy = float(c.centreOfCurvature["x"]), float(c.centreOfCurvature["y"])
        r = np.hypot(x - cocx, y - cocy)
        phi = _norm_phi(np.arctan2(y - cocy, x - cocx))

        z0, z1 = float(c.CavernZ[0]), float(c.CavernZ[1])
        within_z = (z > z0) & (z < z1)

        mask = np.zeros_like(r, dtype=bool)
        for i, (rmin, rmax) in enumerate(simple_rpcs.get("r", [])):
            p_list = simple_rpcs["phi"]["CoC"][i]
            pmin, pmax = float(min(p_list)), float(max(p_list))
            in_r = (r > float(rmin)) & (r < float(rmax))
            if pmin <= pmax:
                in_phi = (phi >= pmin) & (phi <= pmax)
            else:
                in_phi = (phi >= pmin) | (phi <= pmax)
            mask |= in_r & in_phi

        return mask & within_z

    def in_anubis_shaft(self, x: np.ndarray, y: np.ndarray, z: np.ndarray, shaft_rpcs: Dict[str, Any]) -> np.ndarray:
        """
        "Point lies within any shaft RPC slab volume" (proxy for 'in ANUBIS shaft station').
        """
        xs = np.asarray(shaft_rpcs.get("x", []), dtype=float)
        zs = np.asarray(shaft_rpcs.get("z", []), dtype=float)
        ys = shaft_rpcs.get("y", [])
        rads = np.asarray(shaft_rpcs.get("RPCradius", []), dtype=float)
        pipe = shaft_rpcs.get("pipeCutoff", {}) or {}

        cx = pipe.get("x", "")
        cz = pipe.get("z", "")
        cx = None if cx == "" else float(cx)
        cz = None if cz == "" else float(cz)

        mask = np.zeros_like(x, dtype=bool)
        for i in range(len(xs)):
            y0, y1 = float(ys[i][0]), float(ys[i][1])
            in_y = (y >= y0) & (y <= y1)

            dx = x - xs[i]
            dz = z - zs[i]
            in_r = (np.hypot(dx, dz) <= float(rads[i]))

            if cx is not None:
                if cx < 0:
                    in_r &= (dx >= cx)
                else:
                    in_r &= (dx <= cx)
            if cz is not None:
                if cz < 0:
                    in_r &= (dz >= cz)
                else:
                    in_r &= (dz <= cz)

            mask |= in_y & in_r

        return mask
