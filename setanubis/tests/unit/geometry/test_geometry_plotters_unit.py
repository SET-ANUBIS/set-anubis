"""Unit tests for Matplotlib geometry adapters."""

from __future__ import annotations

import matplotlib.pyplot as plt

from SetAnubis.core.Geometry.adapters.plot_matplotlib import (
    MatplotlibGeometryPlotter,
    MatplotlibPlotter,
)


class _Cavern:
    def __init__(self):
        self.calls = []

    def plotCavernXY(self, axes, **kwargs):
        self.calls.append(("xy", axes, kwargs))

    def plotCavernXZ(self, axes, **kwargs):
        self.calls.append(("xz", axes, kwargs))

    def plotCavernZY(self, axes, **kwargs):
        self.calls.append(("zy", axes, kwargs))

    def plotCavern3D(self, axes, **kwargs):
        figure = plt.figure()
        output_axes = figure.add_subplot(projection="3d")
        self.calls.append(("3d", axes, kwargs))
        return figure, output_axes


class _Geometry:
    def __init__(self, cavern):
        self.cav = cavern


def test_projection_plotters_delegate_to_legacy_cavern_methods():
    cavern = _Cavern()
    plotter = MatplotlibGeometryPlotter(_Geometry(cavern))

    figures = [
        plotter.plot_xy(plot_atlas=True, plot_acceptance=True)[0],
        plotter.plot_xz(plot_atlas=True)[0],
        plotter.plot_zy(plot_acceptance=True)[0],
        plotter.plot_3d(plot_atlas=True, plot_acceptance=True)[0],
    ]

    assert [call[0] for call in cavern.calls] == ["xy", "xz", "zy", "3d"]
    assert cavern.calls[0][2] == {"plotATLAS": True, "plotAcceptance": True}
    assert cavern.calls[3][2] == {"plotATLAS": True, "plotAcceptance": True}
    for figure in figures:
        plt.close(figure)


def test_projection_plotters_provide_fallback_figures():
    plotter = MatplotlibGeometryPlotter(object())
    outputs = [
        plotter.plot_xy(),
        plotter.plot_xz(),
        plotter.plot_zy(),
        plotter.plot_3d(),
    ]

    assert outputs[0][1].get_title() == "Cavern XY"
    assert outputs[1][1].get_title() == "Cavern XZ"
    assert outputs[2][1].get_title() == "Cavern ZY"
    assert outputs[3][1].name == "3d"
    for figure, _axes in outputs:
        plt.close(figure)


def test_generic_plotter_saves_and_optionally_shows(monkeypatch, tmp_path):
    cavern = _Cavern()
    shown = []
    monkeypatch.setattr(plt, "show", lambda: shown.append(True))
    output = tmp_path / "geometry.png"

    MatplotlibPlotter().plot(_Geometry(cavern), savepath=str(output), show=True)

    assert output.is_file()
    assert shown == [True]
    plt.close("all")
