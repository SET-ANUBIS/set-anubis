from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from typing import Optional
from ..domain.interfaces import IGeometry, IGeometryPlotter

class MatplotlibGeometryPlotter(IGeometryPlotter):
    def __init__(self, geometry: IGeometry):
        self._cav = getattr(geometry, "cav", geometry)

    def plot_xy(self, plot_atlas: bool = False, plot_acceptance: bool = False):
        fig, ax = plt.subplots()
        if hasattr(self._cav, "plotCavernXY"):
            self._cav.plotCavernXY(ax, plotATLAS=plot_atlas, plotAcceptance=plot_acceptance)
        else:
            ax.text(0.5, 0.5, "plotCavernXY indisponible", ha="center")
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_title("Cavern XY")
        return fig, ax

    def plot_xz(self, plot_atlas: bool = False):
        fig, ax = plt.subplots()
        if hasattr(self._cav, "plotCavernXZ"):
            self._cav.plotCavernXZ(ax, plotATLAS=plot_atlas)
        else:
            ax.text(0.5, 0.5, "plotCavernXZ indisponible", ha="center")
        ax.set_xlabel("x [m]"); ax.set_ylabel("z [m]"); ax.set_title("Cavern XZ")
        return fig, ax

    def plot_zy(self, plot_atlas: bool = False, plot_acceptance: bool = False):
        fig, ax = plt.subplots()
        if hasattr(self._cav, "plotCavernZY"):
            self._cav.plotCavernZY(ax, plotATLAS=plot_atlas, plotAcceptance=plot_acceptance)
        else:
            ax.text(0.5, 0.5, "plotCavernZY indisponible", ha="center")
        ax.set_xlabel("z [m]"); ax.set_ylabel("y [m]"); ax.set_title("Cavern ZY")
        return fig, ax

    def plot_3d(self, plot_atlas: bool = False, plot_acceptance: bool = False):
        if hasattr(self._cav, "plotCavern3D"):
            fig, ax = self._cav.plotCavern3D(None, plotATLAS=plot_atlas, plotAcceptance=plot_acceptance)  # signature legacy
            return fig, ax
        fig = plt.figure()
        ax = fig.add_subplot(projection="3d")
        ax.text2D(0.5, 0.5, "plotCavern3D indisponible", transform=ax.transAxes, ha="center")
        return fig, ax
