"""Regression tests for the packaged HNL production BR calculator."""

from __future__ import annotations

import numpy as np
import pytest

from SetAnubis.examples.Pythia.TestFiles.production_eq import HNLDecayBRCalculator
from SetAnubis.examples.Pythia.TestFiles.Parameters import SimulationParameters
from SetAnubis.examples.Pythia.TestFiles.HNL_eq import _numeric_parameter


def test_hnl_calculator_accepts_flattened_and_legacy_parameter_values():
    calculator = HNLDecayBRCalculator.__new__(HNLDecayBRCalculator)
    calculator.decay_map = {(10, frozenset({1, 2})): "channel"}
    calculator.histograms = {"channel": lambda mass: mass * 2.0}

    assert calculator.calculate(10, (1, 2), {"mN1": 0.5}) == pytest.approx(1.0)
    assert calculator.calculate(10, (1, 2), {"mN1": {"value": 0.75}}) == pytest.approx(
        1.5
    )
    assert calculator.calculate(10, (1, 2), {"mN1": 0.5 + 0j}) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="mN1"):
        calculator.calculate(10, (1, 2), {})
    with pytest.raises(ValueError, match="No decay mapping"):
        calculator.calculate(10, (3, 4), {"mN1": 0.5})


def test_hnl_histogram_parser_uses_declared_mass_bounds_and_all_points(tmp_path):
    table = tmp_path / "table.dat"
    table.write_text(
        "TH1F|demo|BR/U2e|demo mass (GeV)|\n3, 1.0, 4.0\n0, 0.1\n1, 0.2\n2, 0.3\n",
        encoding="utf-8",
    )
    calculator = HNLDecayBRCalculator.__new__(HNLDecayBRCalculator)
    masses, values = calculator._parse_histograms(str(table))["demo"]
    assert np.allclose(masses, [1.0, 2.0, 3.0])
    assert np.allclose(values, [0.1, 0.2, 0.3])


def test_hnl_formula_parameters_are_in_memory_and_accept_flat_values(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(SimulationParameters, "_instance", None)
    parameters = SimulationParameters()
    assert parameters.get_parameter(11, "mass") is not None
    assert not (tmp_path / "db" / "db.json").exists()
    assert _numeric_parameter({"mN1": 1.25}, "mN1") == pytest.approx(1.25)
    assert _numeric_parameter({"mN1": {"value": 1.5 + 0j}}, "mN1") == pytest.approx(1.5)
    with pytest.raises(ValueError, match="required"):
        _numeric_parameter({"mN1": None}, "mN1")
