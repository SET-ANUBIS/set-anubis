"""Focused tests for branching-ratio calculation adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

import SetAnubis.core.BranchingRatio.adapters.input.DecayInterface as interface_mod
import SetAnubis.core.BranchingRatio.adapters.output.DecayProvider as provider_mod
import SetAnubis.core.BranchingRatio.adapters.output.MartyCalculationAdapter as marty_mod
from SetAnubis.core.BranchingRatio.adapters.output.ConstantCalculationAdapter import (
    ConstantCalculationAdapter,
)
from SetAnubis.core.BranchingRatio.adapters.output.FileInterpolationCalculationAdapter import (
    FileInterpolationCalculationAdapter,
)
from SetAnubis.core.BranchingRatio.adapters.output.MadGraphCalculationAdapter import (
    MadGraphCalculationAdapter,
)
from SetAnubis.core.BranchingRatio.adapters.output.UFOCalculationAdapter import (
    UFOCalculationAdapter,
)
from SetAnubis.core.BranchingRatio.domain.BranchingRatioManager import Unit
from SetAnubis.core.BranchingRatio.domain.CalculationStrategy import (
    CalculationDecayStrategy,
)
from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.examples.BranchingRatio.example_BranchingRatioInterface_hnl import (
    main as run_hnl_interface_example,
)


def test_constant_adapter_and_madgraph_provider_contract():
    width = ConstantCalculationAdapter(0.25)
    assert width.calculate(25, MultiSet([22, 22]), {}) == pytest.approx(0.25)
    assert not width.is_br()

    branching_ratio = ConstantCalculationAdapter(0.4, is_br=True)
    assert branching_ratio.is_br()
    with pytest.raises(ValueError, match="cannot be negative"):
        ConstantCalculationAdapter(-1.0)

    adapter = MadGraphCalculationAdapter(
        lambda mother, daughters, parameters: mother + len(daughters) + parameters["x"]
    )
    assert adapter.calculate(10, MultiSet([1, 2]), {"x": 0.5}) == pytest.approx(12.5)
    with pytest.raises(RuntimeError, match="result-provider callable"):
        MadGraphCalculationAdapter().calculate(10, MultiSet([1, 2]), {})


class _FakeUFOManager:
    def __init__(self, path):
        self.path = path
        self.func = {}
        self.prepared = []

    def evaluate_with_sm(self):
        self.prepared.append("evaluate")

    def create_func_caches(self):
        self.prepared.append("cache")
        self.func = {25: {MultiSet([-13, 13]): lambda params: params["g"] * 2}}

    def get_caches(self):
        return self.func, {25: {MultiSet([-13, 13]): ["g"]}}


def test_ufo_provider_uses_shared_decay_manager(monkeypatch):
    monkeypatch.setattr(provider_mod, "DecayUFOManager", _FakeUFOManager)
    adapter = UFOCalculationAdapter("/trusted/ufo", is_br=True)
    assert adapter.is_br()
    assert adapter.calculate(25, MultiSet([13, -13]), {"g": 0.2}) == pytest.approx(0.4)
    assert adapter._provider.decay_manager.prepared == ["evaluate", "cache"]
    functions, parameters = adapter._provider.get_caches()
    assert 25 in functions and parameters[25]
    with pytest.raises(KeyError, match="No UFO decay function"):
        adapter.calculate(25, MultiSet([22, 22]), {"g": 0.2})


def _write_grid(path: Path) -> None:
    path.write_text(
        "x,y,25:-13;13\n0,0,0\n0,1,2\n1,0,4\n1,1,6\n",
        encoding="utf-8",
    )


def test_csv_exact_linear_and_out_of_range_interpolation(tmp_path):
    grid = tmp_path / "grid.csv"
    _write_grid(grid)
    adapter = FileInterpolationCalculationAdapter(
        str(grid), ["x", "y"], format_type="csv"
    )
    assert adapter.calculate(25, MultiSet([-13, 13]), {"x": 1, "y": 0}) == 4.0
    assert adapter.calculate(
        25, MultiSet([-13, 13]), {"x": 0.5, "y": 0.5}
    ) == pytest.approx(3.0)
    with pytest.raises(ValueError, match="outside"):
        adapter.calculate(25, MultiSet([-13, 13]), {"x": 2, "y": 2})
    with pytest.raises(ValueError, match="Missing interpolation parameters"):
        adapter.calculate(25, MultiSet([-13, 13]), {"x": 0.5})
    with pytest.raises(KeyError, match="No column"):
        adapter.calculate(25, MultiSet([22, 22]), {"x": 0.5, "y": 0.5})

    one_dimensional = tmp_path / "line.csv"
    one_dimensional.write_text("x,25:22;22\n0,1\n2,5\n", encoding="utf-8")
    line = FileInterpolationCalculationAdapter(str(one_dimensional), ["x"])
    assert line.calculate(25, MultiSet([22, 22]), {"x": 1}) == pytest.approx(3.0)
    with pytest.raises(ValueError, match="outside"):
        line.calculate(25, MultiSet([22, 22]), {"x": 3})


def test_csv_loader_validation(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("x,25:1;2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        FileInterpolationCalculationAdapter(str(empty), ["x"])
    with pytest.raises(ValueError, match="missing parameter columns"):
        FileInterpolationCalculationAdapter(str(empty), ["y"])
    with pytest.raises(ValueError, match="Unsupported"):
        FileInterpolationCalculationAdapter._choose_sub_strategy("json")


class _FakeMartyManager:
    def __init__(self, model_name):
        self.model_name = model_name
        self.calls = []

    def calculate_process(self, mothers, daughters, model, builder):
        self.calls.append((mothers, daughters, model, builder))
        return 0.125


class _FakeBuilder:
    pass


def test_marty_adapter_passes_model_and_process(monkeypatch):
    monkeypatch.setattr(marty_mod, "MartyManager", _FakeMartyManager)
    monkeypatch.setattr(marty_mod, "MartyFileCopyBuilder", _FakeBuilder)
    model = object()
    adapter = marty_mod.MartyCalculationAdapter(model, "HNL", is_br=False)
    assert adapter.calculate(25, MultiSet([-13, 13]), {"unused": 1}) == pytest.approx(
        0.125
    )
    mothers, daughters, called_model, _ = adapter.manager.calls[0]
    assert mothers == [25] and daughters == [-13, 13] and called_model is model


class _ForwardingManager:
    def __init__(self, checker, model):
        self.checker = checker
        self.model = model
        self.calls = []

    def calculate_decay(self, *args):
        self.calls.append(("get", args))
        return 1.0

    def add_constant_decay(self, *args, **kwargs):
        self.calls.append(("set", args, kwargs))

    def calculate_total_decay(self, *args):
        self.calls.append(("total", args))
        return 2.0

    def calculate_branching_ratios_for_mother(self, *args):
        self.calls.append(("brs", args))
        return []

    def calculate_branching_ratio_for_mother(self, *args):
        self.calls.append(("br", args))
        return 0.5

    def add_decays(self, *args):
        self.calls.append(("add_many", args))

    def get_all_decays(self, *args):
        self.calls.append(("all", args))
        return {}

    def add_special_lifetime(self, *args):
        self.calls.append(("special", args))

    def calculate_lifetime(self, *args):
        self.calls.append(("lifetime", args))
        return 3.0


def test_decay_interface_forwards_all_public_operations(monkeypatch):
    monkeypatch.setattr(interface_mod, "BranchingRatioManager", _ForwardingManager)
    api = interface_mod.DecayInterface(object())
    assert api.get_decay(25, [22, 22]) == 1.0
    api.set_decay(25, [22, 22], 0.1, is_br=True)
    assert api.get_decay_tot(25) == 2.0
    assert api.get_brs(25) == []
    assert api.get_br(25, [22, 22]) == 0.5
    api.add_decays([], CalculationDecayStrategy.PYTHON, {"script_path": "x.py"})
    assert api.get_all_decays() == {}
    api.add_special_lifetime(25, 1.0, Unit.MM)
    assert api.calculate_lifetime(25, Unit.S) == 3.0
    assert {call[0] for call in api.br_manager.calls} == {
        "get",
        "set",
        "total",
        "brs",
        "br",
        "add_many",
        "all",
        "special",
        "lifetime",
    }


def test_branching_ratio_interface_example_uses_an_interior_csv_point(capsys):
    run_hnl_interface_example()
    output = capsys.readouterr().out
    assert "[PYTHON] Gamma(H -> b bbar)" in output
    assert "[CSV] Gamma(H -> mu+ mu-) = 0.0105" in output
    assert "branching_ratio" in output
