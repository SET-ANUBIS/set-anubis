from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple
import numpy as np
import plotly.graph_objects as go

from SetAnubis.HepMCGUI.defineGeometry import ATLASCavern

EDGE_COLOR = "rgba(226,232,240,0.55)"
ATLAS_COLOR = "rgba(96,165,250,0.55)"
BOX_FILL = "rgba(148,163,184,0.04)"

@dataclass(frozen=True)
class Cavern3DFigureFactory:
    """
    Lightweight 3D representation:
    - Cavern bounding box edges (x,y,z)
    - ATLAS envelope cylinder (approx)
    Meant as an interactive 3D context for vertex clouds.
    """
    cavern: ATLASCavern

    def _line3d(self, xs, ys, zs, name: str, width: int = 3, color: str = EDGE_COLOR):
        return go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", name=name,
                            line=dict(width=width, color=color),
                            hoverinfo="skip", showlegend=False)

    def cavern_box_edges(self) -> list[go.BaseTraceType]:
        c = self.cavern
        x0, x1 = c.CavernX
        z0, z1 = c.CavernZ
        y0 = c.CavernY[0]
        y1 = c.archRadius + c.centreOfCurvature["y"]

        # 8 corners
        corners = [
            (x0,y0,z0), (x1,y0,z0), (x1,y0,z1), (x0,y0,z1),
            (x0,y1,z0), (x1,y1,z0), (x1,y1,z1), (x0,y1,z1),
        ]
        # edges as pairs of indices
        edges = [
            (0,1),(1,2),(2,3),(3,0),  # bottom
            (4,5),(5,6),(6,7),(7,4),  # top
            (0,4),(1,5),(2,6),(3,7),  # verticals
        ]
        traces = []
        for a,b in edges:
            xa,ya,za = corners[a]
            xb,yb,zb = corners[b]
            traces.append(self._line3d([xa,xb],[ya,yb],[za,zb], "cavern"))
        return traces

    def atlas_cylinder(self, n_phi: int = 120) -> list[go.BaseTraceType]:
        c = self.cavern
        r = c.radiusATLAS
        x0 = c.ATLAS_Centre["x"]
        y0 = c.ATLAS_Centre["y"]
        zmin, zmax = c.ATLAS_Z

        phis = np.linspace(0, 2*np.pi, n_phi)
        xs = x0 + r*np.cos(phis)
        ys = y0 + r*np.sin(phis)

        # top/bottom rings
        top = go.Scatter3d(x=xs, y=ys, z=np.full_like(xs, zmax),
                           mode="lines", line=dict(width=4, color=ATLAS_COLOR),
                           hoverinfo="skip", showlegend=False)
        bot = go.Scatter3d(x=xs, y=ys, z=np.full_like(xs, zmin),
                           mode="lines", line=dict(width=4, color=ATLAS_COLOR),
                           hoverinfo="skip", showlegend=False)

        # a few verticals to suggest the surface
        traces = [top, bot]
        for k in range(0, n_phi, max(1, n_phi//12)):
            traces.append(go.Scatter3d(
                x=[xs[k], xs[k]], y=[ys[k], ys[k]], z=[zmin, zmax],
                mode="lines", line=dict(width=2, color="rgba(96,165,250,0.35)"),
                hoverinfo="skip", showlegend=False
            ))
        return traces

    def base_figure(self, show_box: bool = True, show_atlas: bool = True) -> go.Figure:
        fig = go.Figure()
        if show_box:
            for t in self.cavern_box_edges():
                fig.add_trace(t)
        if show_atlas:
            for t in self.atlas_cylinder():
                fig.add_trace(t)

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10,r=10,t=40,b=10),
            scene=dict(
                xaxis_title="x [m]",
                yaxis_title="y [m]",
                zaxis_title="z [m]",
                xaxis=dict(showbackground=False, gridcolor="rgba(148,163,184,0.12)"),
                yaxis=dict(showbackground=False, gridcolor="rgba(148,163,184,0.12)"),
                zaxis=dict(showbackground=False, gridcolor="rgba(148,163,184,0.12)"),
                aspectmode="data",
                camera=dict(eye=dict(x=1.45, y=1.25, z=1.10)),
            ),
            showlegend=False,
            title="ATLAS cavern (3D)",
        )
        return fig
