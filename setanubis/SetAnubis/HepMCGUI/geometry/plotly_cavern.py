from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import plotly.graph_objects as go

CAVERN_LINE_COLOR = "rgba(226,232,240,0.70)"  # light slate
CAVERN_SOFT_FILL = "rgba(148,163,184,0.10)"

from SetAnubis.HepMCGUI.defineGeometry import ATLASCavern

@dataclass(frozen=True)
class CavernFigureFactory:
    """
    Build Plotly figures for cavern projections.

    Single responsibility: translate ATLASCavern geometry to Plotly primitives (traces + shapes).
    """
    cavern: ATLASCavern

    def _add_line(self, fig: go.Figure, x0, y0, x1, y1, width: int = 2, dash: str = "solid"):
        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                      line=dict(width=width, dash=dash, color=CAVERN_LINE_COLOR))

    def _add_rect(self, fig: go.Figure, x0, y0, x1, y1, width: int = 2, dash: str = "solid", fill: Optional[str] = None, opacity: float = 0.15):
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                      line=dict(width=width, dash=dash, color=CAVERN_LINE_COLOR),
                      fillcolor=(fill if fill is not None else CAVERN_SOFT_FILL),
                      opacity=opacity)

    def _add_circle(self, fig: go.Figure, xc, yc, r, width: int = 2, dash: str = "solid"):
        fig.add_shape(type="circle", x0=xc-r, y0=yc-r, x1=xc+r, y1=yc+r,
                      line=dict(width=width, dash=dash, color=CAVERN_LINE_COLOR))

    def _add_curve(self, fig: go.Figure, xs: Sequence[float], ys: Sequence[float], name: str = "curve"):
        fig.add_trace(go.Scatter(x=list(xs), y=list(ys), mode="lines", name=name))

    def figure_xy(self, plot_atlas: bool = True, plot_acceptance: bool = False) -> go.Figure:
        c = self.cavern
        fig = go.Figure()

        # cavern bounds (verticals)
        self._add_line(fig, c.CavernX[0], c.CavernY[0], c.CavernX[0], c.CavernY[1])
        self._add_line(fig, c.CavernX[1], c.CavernY[0], c.CavernX[1], c.CavernY[1])

        # trench
        self._add_line(fig, c.CavernTrench["X"][0], c.CavernTrench["Y"][0], c.CavernTrench["X"][0], c.CavernTrench["Y"][1])
        self._add_line(fig, c.CavernTrench["X"][1], c.CavernTrench["Y"][0], c.CavernTrench["X"][1], c.CavernTrench["Y"][1])
        self._add_line(fig, c.CavernTrench["X"][0], c.CavernTrench["Y"][0], c.CavernTrench["X"][1], c.CavernTrench["Y"][0])

        # hatched rectangles (approx with semi-transparent fill)
        self._add_rect(fig, c.CavernX[0], c.CavernTrench["Y"][0], c.CavernTrench["X"][0], c.CavernY[0], fill="rgba(148,163,184,0.14)")
        self._add_rect(fig, c.CavernTrench["X"][1], c.CavernTrench["Y"][0], c.CavernX[1], c.CavernY[0], fill="rgba(148,163,184,0.14)")

        # ceiling arch
        arch = c.createCavernVault(doPlot=False)
        self._add_curve(fig, arch["x"], arch["y"], name="ceiling")

        # shafts (PX14/PX16 as 2 verticals each)
        for shaft in ["PX14", "PX16"]:
            centre = getattr(c, f"{shaft}_Centre")
            radius = getattr(c, f"{shaft}_Radius")
            lowestY = getattr(c, f"{shaft}_LowestY")
            height = getattr(c, f"{shaft}_Height")
            y0 = lowestY
            y1 = centre["y"] + height
            self._add_line(fig, centre["x"]-radius, y0, centre["x"]-radius, y1, dash="dash")
            self._add_line(fig, centre["x"]+radius, y0, centre["x"]+radius, y1, dash="dash")

        # points: cavern centre + IP + CoC
        fig.add_trace(go.Scatter(
            x=[0, c.IP["x"], c.centreOfCurvature["x"]],
            y=[0, c.IP["y"], c.centreOfCurvature["y"]],
            mode="markers+text",
            marker=dict(size=10, color="rgba(96,165,250,0.95)", line=dict(width=1, color="rgba(226,232,240,0.65)")),
            text=["Centre", "IP", "CoC"],
            textposition="top right",
            name="refs"
        ))

        # ATLAS envelope (circle)
        if plot_atlas:
            self._add_circle(fig, c.ATLAS_Centre["x"], c.ATLAS_Centre["y"], c.radiusATLAS, dash="dash")
            if getattr(c, "includeATLASlimit", True):
                self._add_circle(fig, c.ATLAS_Centre["x"], c.ATLAS_Centre["y"], c.radiusATLAStracking, dash="dot")

        if plot_acceptance:
            self._add_line(fig, c.IP["x"], c.IP["y"], c.CavernX[0], c.CavernY[1], dash="dash")
            self._add_line(fig, c.IP["x"], c.IP["y"], c.CavernX[1], c.CavernY[1], dash="dash")

        fig.update_layout(
            title="ATLAS cavern (XY)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(229,231,235,0.92)"),
            xaxis_title="x [m]",
            yaxis_title="y [m]",
            xaxis=dict(range=[-18, 18], zeroline=False, gridcolor="rgba(148,163,184,0.12)", zerolinecolor="rgba(148,163,184,0.12)"),
            yaxis=dict(range=[-18, 25], zeroline=False, gridcolor="rgba(148,163,184,0.12)", zerolinecolor="rgba(148,163,184,0.12)"),
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        return fig

    def figure_xz(self, plot_atlas: bool = True) -> go.Figure:
        c = self.cavern
        fig = go.Figure()

        # cavern rectangle (x vs z)
        self._add_rect(fig, c.CavernX[0], c.CavernZ[0], c.CavernX[1], c.CavernZ[1], opacity=0.0)

        # shafts circles
        self._add_circle(fig, c.PX14_Centre["x"], c.PX14_Centre["z"], c.PX14_Radius, dash="dash")
        self._add_circle(fig, c.PX16_Centre["x"], c.PX16_Centre["z"], c.PX16_Radius, dash="dash")

        # refs
        fig.add_trace(go.Scatter(
            x=[0, c.IP["x"]],
            y=[0, c.IP["z"]],
            mode="markers+text",
            marker=dict(size=10, color="rgba(96,165,250,0.95)", line=dict(width=1, color="rgba(226,232,240,0.65)")),
            text=["Centre", "IP"],
            textposition="top right",
            name="refs"
        ))

        if plot_atlas:
            # ATLAS rectangle in XZ
            self._add_rect(fig, c.ATLAS_Centre["x"]-c.radiusATLAS, c.ATLAS_Z[0], c.ATLAS_Centre["x"]+c.radiusATLAS, c.ATLAS_Z[1],
                           dash="dash", opacity=0.0)

        fig.update_layout(
            title="ATLAS cavern (XZ)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(229,231,235,0.92)"),
            xaxis_title="x [m]",
            yaxis_title="z [m]",
            xaxis=dict(range=[-18, 18], zeroline=False, gridcolor="rgba(148,163,184,0.12)", zerolinecolor="rgba(148,163,184,0.12)"),
            yaxis=dict(range=[-30, 30], zeroline=False, gridcolor="rgba(148,163,184,0.12)", zerolinecolor="rgba(148,163,184,0.12)"),
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        return fig

    def figure_zy(self, plot_atlas: bool = True, plot_acceptance: bool = False) -> go.Figure:
        c = self.cavern
        fig = go.Figure()

        # cavern "walls" in ZY
        if getattr(c, "includeCavernYinZY", True):
            self._add_line(fig, c.CavernZ[0], c.CavernY[1], c.CavernZ[1], c.CavernY[1], dash="dash")

        topY = c.archRadius + c.centreOfCurvature["y"]
        self._add_line(fig, c.CavernZ[0], c.CavernY[0], c.CavernZ[0], topY)
        self._add_line(fig, c.CavernZ[1], c.CavernY[0], c.CavernZ[1], topY)
        self._add_line(fig, c.CavernZ[0], topY, c.CavernZ[1], topY)

        # trench
        self._add_line(fig, c.CavernTrench["Z"][0], c.CavernTrench["Y"][0], c.CavernTrench["Z"][0], c.CavernTrench["Y"][1])
        self._add_line(fig, c.CavernTrench["Z"][1], c.CavernTrench["Y"][0], c.CavernTrench["Z"][1], c.CavernTrench["Y"][1])
        self._add_line(fig, c.CavernTrench["Z"][0], c.CavernTrench["Y"][0], c.CavernTrench["Z"][1], c.CavernTrench["Y"][0])

        # shafts as verticals in ZY (z = centre ± radius)
        for shaft in ["PX14", "PX16"]:
            centre = getattr(c, f"{shaft}_Centre")
            radius = getattr(c, f"{shaft}_Radius")
            height = getattr(c, f"{shaft}_Height")
            y0 = centre["y"]
            y1 = centre["y"] + height
            self._add_line(fig, centre["z"]-radius, y0, centre["z"]-radius, y1, dash="dash")
            self._add_line(fig, centre["z"]+radius, y0, centre["z"]+radius, y1, dash="dash")

        # refs (note: Z on x-axis here)
        fig.add_trace(go.Scatter(
            x=[0, c.IP["z"]],
            y=[0, c.IP["y"]],
            mode="markers+text",
            marker=dict(size=10, color="rgba(96,165,250,0.95)", line=dict(width=1, color="rgba(226,232,240,0.65)")),
            text=["Centre", "IP"],
            textposition="top right",
            name="refs"
        ))

        if plot_atlas:
            # ATLAS rectangle in ZY
            self._add_rect(fig, c.ATLAS_Z[0], c.ATLAS_Centre["y"]-c.radiusATLAS, c.ATLAS_Z[1], c.ATLAS_Centre["y"]+c.radiusATLAS,
                           dash="dash", opacity=0.0)
            if getattr(c, "includeATLASlimit", True):
                self._add_line(fig, c.ATLAS_Z[0], c.ATLAS_Centre["y"]-c.radiusATLAStracking, c.ATLAS_Z[1], c.ATLAS_Centre["y"]-c.radiusATLAStracking, dash="dot")
                self._add_line(fig, c.ATLAS_Z[0], c.ATLAS_Centre["y"]+c.radiusATLAStracking, c.ATLAS_Z[1], c.ATLAS_Centre["y"]+c.radiusATLAStracking, dash="dot")

        if plot_acceptance:
            self._add_line(fig, c.IP["z"], c.IP["y"], c.CavernZ[0], c.CavernY[1], dash="dash")
            self._add_line(fig, c.IP["z"], c.IP["y"], c.CavernZ[1], c.CavernY[1], dash="dash")

        fig.update_layout(
            title="ATLAS cavern (ZY)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(229,231,235,0.92)"),
            xaxis_title="z [m]",
            yaxis_title="y [m]",
            xaxis=dict(range=[-30, 30], zeroline=False, gridcolor="rgba(148,163,184,0.12)", zerolinecolor="rgba(148,163,184,0.12)"),
            yaxis=dict(range=[-18, 25], zeroline=False, gridcolor="rgba(148,163,184,0.12)", zerolinecolor="rgba(148,163,184,0.12)"),
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        return fig
