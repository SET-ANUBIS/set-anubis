from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, Any, List

import numpy as np
import plotly.graph_objects as go

from defineGeometry import ATLASCavern


def _norm_phi(phi: np.ndarray) -> np.ndarray:
    """Normalize angles to [0, 2pi)."""
    out = np.mod(phi, 2 * np.pi)
    out[out < 0] += 2 * np.pi
    return out


@dataclass(frozen=True)
class AnubisOverlayFactory:
    """
    Plotly overlays for ANUBIS-related geometry (as defined in defineGeometry/_plotGeometry).

    Supports:
      - "simple ceiling" stations from ATLASCavern.createSimpleRPCs()
      - "shaft" stations from ATLASCavern.createShaftRPCs()

    Single responsibility: translate station dictionaries -> plotly traces.
    """
    cavern: ATLASCavern

    layer_colors: Tuple[str, ...] = (
        "rgba(167,139,250,0.75)",  # violet
        "rgba(96,165,250,0.75)",   # blue
        "rgba(129,140,248,0.72)",  # indigo
        "rgba(139,92,246,0.70)",   # purple
    )

    def _shaft_rpc_shape_xz(
        self,
        x_offset: float,
        z_offset: float,
        pipe_cutoff: Dict[str, Any],
        radius: float,
        n: int = 240,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Port of shaftRPCshape() from _plotGeometry.py:
        returns boundary polyline (x,z) with optional cutoffs (flattened sides).
        """
        ang = np.linspace(0, 2 * np.pi, n, endpoint=True)
        x = radius * np.sin(ang)
        z = radius * np.cos(ang)

        cx = pipe_cutoff.get("x", "")
        cz = pipe_cutoff.get("z", "")

        if cx != "" and cx is not None:
            cx = float(cx)
            if cx < 0:
                x = np.maximum(x, cx)
            else:
                x = np.minimum(x, cx)

        if cz != "" and cz is not None:
            cz = float(cz)
            if cz < 0:
                z = np.maximum(z, cz)
            else:
                z = np.minimum(z, cz)

        return x + float(x_offset), z + float(z_offset)

    # ---------------------------
    # Simple ceiling stations
    # ---------------------------
    def add_simple_rpcs_xy(self, fig: go.Figure, simple_rpcs: Dict[str, Any], name: str = "ANUBIS ceiling") -> None:
        cocx = float(self.cavern.centreOfCurvature["x"])
        cocy = float(self.cavern.centreOfCurvature["y"])

        phis_all = simple_rpcs["phi"]["CoC"]
        rs = simple_rpcs["r"]

        for i, (rmin, rmax) in enumerate(rs):
            color = self.layer_colors[i % len(self.layer_colors)]
            phi_min = float(min(phis_all[i]))
            phi_max = float(max(phis_all[i]))

            if phi_min <= phi_max:
                phis = np.linspace(phi_min, phi_max, 220)
            else:
                # wrap through 2pi
                phis = np.concatenate([
                    np.linspace(phi_min, 2*np.pi, 110),
                    np.linspace(0.0, phi_max, 110),
                ])

            def arc(r):
                x = cocx + float(r) * np.cos(phis)
                y = cocy + float(r) * np.sin(phis)
                return x, y

            x1, y1 = arc(rmin)
            x2, y2 = arc(rmax)

            fig.add_trace(go.Scatter(
                x=x1, y=y1, mode="lines",
                line=dict(width=2, color=color),
                name=f"{name} (layer {i})",
                hoverinfo="skip",
                showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=x2, y=y2, mode="lines",
                line=dict(width=2, color=color),
                hoverinfo="skip",
                showlegend=False,
            ))

            # connect ends to show thickness (subtle)
            fig.add_trace(go.Scatter(
                x=[x1[0], x2[0]], y=[y1[0], y2[0]],
                mode="lines",
                line=dict(width=1, color="rgba(226,232,240,0.22)"),
                hoverinfo="skip",
                showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=[x1[-1], x2[-1]], y=[y1[-1], y2[-1]],
                mode="lines",
                line=dict(width=1, color="rgba(226,232,240,0.22)"),
                hoverinfo="skip",
                showlegend=False,
            ))

    def add_simple_rpcs_3d(self, fig: go.Figure, simple_rpcs: Dict[str, Any], name: str = "ANUBIS ceiling") -> None:
        """
        Approx 3D: draw cylinder arcs at z=min/max of cavern for each layer.
        """
        cocx = float(self.cavern.centreOfCurvature["x"])
        cocy = float(self.cavern.centreOfCurvature["y"])
        z0, z1 = float(self.cavern.CavernZ[0]), float(self.cavern.CavernZ[1])

        phis_all = simple_rpcs["phi"]["CoC"]
        rs = simple_rpcs["r"]

        for i, (rmin, rmax) in enumerate(rs):
            color = self.layer_colors[i % len(self.layer_colors)]
            phi_min = float(min(phis_all[i]))
            phi_max = float(max(phis_all[i]))

            if phi_min <= phi_max:
                phis = np.linspace(phi_min, phi_max, 240)
            else:
                phis = np.concatenate([
                    np.linspace(phi_min, 2*np.pi, 120),
                    np.linspace(0.0, phi_max, 120),
                ])

            # use outer radius for a visible envelope
            r = float(rmax)
            xs = cocx + r * np.cos(phis)
            ys = cocy + r * np.sin(phis)

            for zz in (z0, z1):
                fig.add_trace(go.Scatter3d(
                    x=xs, y=ys, z=np.full_like(xs, zz),
                    mode="lines",
                    line=dict(width=4, color=color),
                    hoverinfo="skip",
                    showlegend=False,
                ))

            # a few verticals
            for k in range(0, len(xs), max(1, len(xs)//10)):
                fig.add_trace(go.Scatter3d(
                    x=[xs[k], xs[k]], y=[ys[k], ys[k]], z=[z0, z1],
                    mode="lines",
                    line=dict(width=2, color="rgba(226,232,240,0.14)"),
                    hoverinfo="skip",
                    showlegend=False,
                ))

    # ---------------------------
    # Shaft stations
    # ---------------------------
    def add_shaft_rpcs_xz(self, fig: go.Figure, shaft_rpcs: Dict[str, Any], name: str = "ANUBIS shaft") -> None:
        pipe_cutoff = shaft_rpcs.get("pipeCutoff", {})
        xs0 = shaft_rpcs["x"]
        zs0 = shaft_rpcs["z"]
        rads = shaft_rpcs["RPCradius"]

        for i in range(len(xs0)):
            color = self.layer_colors[i % len(self.layer_colors)]
            xs, zs = self._shaft_rpc_shape_xz(xs0[i], zs0[i], pipe_cutoff, rads[i])
            fig.add_trace(go.Scatter(
                x=xs, y=zs, mode="lines",
                line=dict(width=2, color=color),
                name=f"{name} (layer {i})",
                hoverinfo="skip",
                showlegend=False,
            ))

    def add_shaft_rpcs_xy(self, fig: go.Figure, shaft_rpcs: Dict[str, Any], name: str = "ANUBIS shaft") -> None:
        pipe_cutoff = shaft_rpcs.get("pipeCutoff", {})
        xs0 = shaft_rpcs["x"]
        zs0 = shaft_rpcs["z"]
        ys0 = shaft_rpcs["y"]
        rads = shaft_rpcs["RPCradius"]

        for i in range(len(xs0)):
            color = self.layer_colors[i % len(self.layer_colors)]
            xs, _zs = self._shaft_rpc_shape_xz(xs0[i], zs0[i], pipe_cutoff, rads[i])
            y_lo, y_hi = float(ys0[i][0]), float(ys0[i][1])

            fig.add_trace(go.Scatter(x=xs, y=np.full_like(xs, y_lo), mode="lines",
                                     line=dict(width=2, color=color), hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(x=xs, y=np.full_like(xs, y_hi), mode="lines",
                                     line=dict(width=2, color=color), hoverinfo="skip", showlegend=False))

    def add_shaft_rpcs_zy(self, fig: go.Figure, shaft_rpcs: Dict[str, Any], name: str = "ANUBIS shaft") -> None:
        pipe_cutoff = shaft_rpcs.get("pipeCutoff", {})
        xs0 = shaft_rpcs["x"]
        zs0 = shaft_rpcs["z"]
        ys0 = shaft_rpcs["y"]
        rads = shaft_rpcs["RPCradius"]

        for i in range(len(xs0)):
            color = self.layer_colors[i % len(self.layer_colors)]
            _xs, zs = self._shaft_rpc_shape_xz(xs0[i], zs0[i], pipe_cutoff, rads[i])
            y_lo, y_hi = float(ys0[i][0]), float(ys0[i][1])

            fig.add_trace(go.Scatter(x=zs, y=np.full_like(zs, y_lo), mode="lines",
                                     line=dict(width=2, color=color), hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(x=zs, y=np.full_like(zs, y_hi), mode="lines",
                                     line=dict(width=2, color=color), hoverinfo="skip", showlegend=False))

    def add_shaft_rpcs_3d(self, fig: go.Figure, shaft_rpcs: Dict[str, Any], name: str = "ANUBIS shaft") -> None:
        pipe_cutoff = shaft_rpcs.get("pipeCutoff", {})
        xs0 = shaft_rpcs["x"]
        zs0 = shaft_rpcs["z"]
        ys0 = shaft_rpcs["y"]
        rads = shaft_rpcs["RPCradius"]

        for i in range(len(xs0)):
            color = self.layer_colors[i % len(self.layer_colors)]
            xs, zs = self._shaft_rpc_shape_xz(xs0[i], zs0[i], pipe_cutoff, rads[i])
            y_lo, y_hi = float(ys0[i][0]), float(ys0[i][1])

            for yy in (y_lo, y_hi):
                fig.add_trace(go.Scatter3d(
                    x=xs, y=np.full_like(xs, yy), z=zs,
                    mode="lines",
                    line=dict(width=4, color=color),
                    hoverinfo="skip",
                    showlegend=False,
                ))
