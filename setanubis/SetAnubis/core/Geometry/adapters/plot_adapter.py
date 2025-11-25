from __future__ import annotations
from typing import Optional
from ..domain.interfaces import IGeometry, IGeometryPlotter
from SetAnubis.core.Geometry.adapters.plot_matplotlib import plotCavern 

class MatplotlibPlotter(IGeometryPlotter):
    def plot(self, geometry: IGeometry, *, show: bool = True, savepath: Optional[str] = None) -> None:
        fig = plotCavern(geometry)
        if savepath:
            fig.savefig(savepath, dpi=150, bbox_inches="tight")
        if show:
            import matplotlib.pyplot as plt
            plt.show()
