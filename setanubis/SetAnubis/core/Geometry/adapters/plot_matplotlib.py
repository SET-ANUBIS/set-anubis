"""Matplotlib rendering helpers for cavern geometry implementations."""

from __future__ import annotations

import matplotlib.pyplot as plt

from ..domain.interfaces import IGeometry, IGeometryPlotter


class MatplotlibGeometryPlotter:
    """Render the available legacy cavern projections with Matplotlib."""

    def __init__(self, geometry: IGeometry) -> None:
        """Store either a geometry wrapper or its underlying cavern object."""
        self._cav = getattr(geometry, "cav", geometry)

    def plot_xy(
        self, plot_atlas: bool = False, plot_acceptance: bool = False
    ):
        """Return a figure showing the cavern in the x-y projection."""
        figure, axes = plt.subplots()
        if hasattr(self._cav, "plotCavernXY"):
            self._cav.plotCavernXY(
                axes,
                plotATLAS=plot_atlas,
                plotAcceptance=plot_acceptance,
            )
        else:
            axes.text(0.5, 0.5, "plotCavernXY unavailable", ha="center")
        axes.set_xlabel("x [m]")
        axes.set_ylabel("y [m]")
        axes.set_title("Cavern XY")
        return figure, axes

    def plot_xz(self, plot_atlas: bool = False):
        """Return a figure showing the cavern in the x-z projection."""
        figure, axes = plt.subplots()
        if hasattr(self._cav, "plotCavernXZ"):
            self._cav.plotCavernXZ(axes, plotATLAS=plot_atlas)
        else:
            axes.text(0.5, 0.5, "plotCavernXZ unavailable", ha="center")
        axes.set_xlabel("x [m]")
        axes.set_ylabel("z [m]")
        axes.set_title("Cavern XZ")
        return figure, axes

    def plot_zy(
        self, plot_atlas: bool = False, plot_acceptance: bool = False
    ):
        """Return a figure showing the cavern in the z-y projection."""
        figure, axes = plt.subplots()
        if hasattr(self._cav, "plotCavernZY"):
            self._cav.plotCavernZY(
                axes,
                plotATLAS=plot_atlas,
                plotAcceptance=plot_acceptance,
            )
        else:
            axes.text(0.5, 0.5, "plotCavernZY unavailable", ha="center")
        axes.set_xlabel("z [m]")
        axes.set_ylabel("y [m]")
        axes.set_title("Cavern ZY")
        return figure, axes

    def plot_3d(
        self, plot_atlas: bool = False, plot_acceptance: bool = False
    ):
        """Return a 3-D cavern figure or a labelled fallback figure."""
        if hasattr(self._cav, "plotCavern3D"):
            return self._cav.plotCavern3D(
                None,
                plotATLAS=plot_atlas,
                plotAcceptance=plot_acceptance,
            )
        figure = plt.figure()
        axes = figure.add_subplot(projection="3d")
        axes.text2D(
            0.5,
            0.5,
            "plotCavern3D unavailable",
            transform=axes.transAxes,
            ha="center",
        )
        return figure, axes


class MatplotlibPlotter(IGeometryPlotter):
    """Implement the generic geometry plotter port with a 3-D view."""

    def plot(
        self,
        geometry: IGeometry,
        *,
        show: bool = True,
        savepath: str | None = None,
    ) -> None:
        """Render, optionally save, and optionally display the geometry."""
        figure, _axes = MatplotlibGeometryPlotter(geometry).plot_3d()
        if savepath:
            figure.savefig(savepath, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
