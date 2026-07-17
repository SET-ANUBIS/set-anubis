
import math
import types
import pytest

import SetAnubis.core.BranchingRatio.domain.BranchingRatioManager as br_mod
from SetAnubis.core.BranchingRatio.domain.CalculationStrategy import CalculationDecayStrategy
from SetAnubis.core.BranchingRatio.domain.BranchingRatioManager import Unit, convert_lifetime


class FakeDecayChecker:
    def __init__(self):
        self.calls = []
    def check_decay_validity(self, mother, daughters, nsa):
        self.calls.append((mother, tuple(sorted(daughters))))

class FakeNSA:
    def __init__(self, masses, params):
        self._m = {int(k): complex(v) for k, v in masses.items()}
        self._params = dict(params)
    def get_particle_mass(self, pdg):
        return self._m[int(abs(pdg))]
    def get_all_parameters(self):
        return dict(self._params)

class FakeAdapterBase:
    def __init__(self, is_br=False):
        self._is_br = is_br
    def is_br(self):
        return self._is_br

class FakeUFOAdapter(FakeAdapterBase):
    def __init__(self, ufo_path, is_br=False):
        super().__init__(is_br=is_br)
        self.ufo_path = ufo_path
    def calculate(self, mother, daughters, parameters):
        return 2.0

class FakePythonAdapter(FakeAdapterBase):
    def __init__(self, script_path, is_br=False):
        super().__init__(is_br=is_br)
        self.script_path = script_path
    def calculate(self, mother, daughters, parameters):
        return float(parameters.get("g", 0.0)) + 1.0

class FakeFileInterpAdapter(FakeAdapterBase):
    def __init__(self, file_path, varying_params, is_br=False, format_type="csv"):
        super().__init__(is_br=is_br)
        self.file_path = file_path
        self.varying = list(varying_params)
        self.format_type = format_type
    def calculate(self, mother, daughters, parameters):
        return sum(float(parameters.get(p, 0.0)) for p in self.varying) + 0.5

class FakeZeroAdapter(FakeAdapterBase):
    def __init__(self, *args, **kwargs):
        super().__init__(is_br=kwargs.get("is_br", False))
        self.args = args
        self.kwargs = kwargs
    def calculate(self, mother, daughters, parameters): return 0.0


@pytest.fixture(autouse=True)
def patch_adapters(monkeypatch):
    monkeypatch.setattr(br_mod, "UFOCalculationAdapter",    FakeUFOAdapter,    raising=True)
    monkeypatch.setattr(br_mod, "PythonCalculationAdapter", FakePythonAdapter, raising=True)
    monkeypatch.setattr(br_mod, "FileInterpolationCalculationAdapter", FakeFileInterpAdapter, raising=True)
    monkeypatch.setattr(br_mod, "MadGraphCalculationAdapter", FakeZeroAdapter, raising=True)
    monkeypatch.setattr(br_mod, "MartyCalculationAdapter",    FakeZeroAdapter, raising=True)


def make_mgr(masses=None, params=None):
    masses = masses or {100: 5.0, 1: 1.0, 2: 2.0, 3: 3.0}
    params = params or {"g": 0.4}
    checker = FakeDecayChecker()
    nsa = FakeNSA(masses=masses, params=params)
    return br_mod.BranchingRatioManager(checker, nsa), checker


def test_add_and_calculate_decay_python_strategy():
    mgr, checker = make_mgr()
    mgr.add_decay(
        mother=100,
        daughters=[1,2],
        strategy=CalculationDecayStrategy.PYTHON,
        config={"script_path": "/tmp/whatever.py", "BR": False}
    )
    w = mgr.calculate_decay(100, [1,2])
    assert w == pytest.approx(1.4, rel=1e-12)
    assert (100, (1,2)) in checker.calls


def test_model_parameter_metadata_is_flattened_before_calculation():
    mgr, _ = make_mgr(params={
        "g": {"value": 0.4 + 0j, "lhablock": "COUPLINGS"},
        "phase": {"value": 0.2 + 0.3j, "lhablock": None},
    })
    mgr.add_decay(
        100,
        [1, 2],
        CalculationDecayStrategy.PYTHON,
        {"script_path": "x.py", "BR": False},
    )

    assert mgr.calculate_decay(100, [1, 2]) == pytest.approx(1.4)
    flattened = mgr._numeric_parameters(mgr.nsa.get_all_parameters())
    assert flattened["g"] == pytest.approx(0.4)
    assert flattened["phase"] == 0.2 + 0.3j


def test_mass_threshold_returns_zero():
    mgr, _ = make_mgr(masses={100: 3.0, 1: 1.5, 2: 1.5})
    mgr.add_decay(100, [1,2], CalculationDecayStrategy.UFO, {"ufo_path": "/dev/null", "BR": False})
    assert mgr.calculate_decay(100, [1,2]) == 0.0


def test_total_width_and_branching_ratios():
    mgr, _ = make_mgr(params={"g": 1.0})
    # - PYTHON -> 1.0 + 1.0 = 2.0
    # FILE_INTERPOLATION on ["g"] produces g + 0.5 = 1.5
    mgr.add_decay(100, [1,2], CalculationDecayStrategy.PYTHON, {"script_path": "x.py", "BR": False})
    mgr.add_decay(100, [1,3], CalculationDecayStrategy.FILE_INTERPOLATION, {"file_path": "x.csv", "varying_params": ["g"], "BR": False})

    total = mgr.calculate_total_decay(100)
    assert total == pytest.approx(3.5, rel=1e-12)

    brs = mgr.calculate_branching_ratios_for_mother(100)
    d = {tuple(sorted(x["daughters"])): x for x in brs}
    assert d[(1,2)]["branching_ratio"] == pytest.approx(2.0/3.5, rel=1e-12)
    assert d[(1,3)]["branching_ratio"] == pytest.approx(1.5/3.5, rel=1e-12)

    br_single = mgr.calculate_branching_ratio_for_mother(100, [1,2])
    assert br_single == pytest.approx(2.0/3.5, rel=1e-12)


def test_is_br_passthrough():
    mgr, _ = make_mgr(params={"g": 0.0})
    mgr.add_decay(100, [1,2], CalculationDecayStrategy.PYTHON, {"script_path": "x.py", "BR": True})
    mgr.add_decay(100, [1,3], CalculationDecayStrategy.UFO, {"ufo_path": "/dev/null", "BR": False})
    # FakePythonAdapter: g+1.0 = 1.0 -> alredy BR
    brs = mgr.calculate_branching_ratios_for_mother(100)
    br_d12 = [x for x in brs if tuple(sorted(x["daughters"])) == (1,2)][0]["branching_ratio"]
    assert br_d12 == pytest.approx(1.0, rel=1e-12)


def test_add_decays_bulk_and_get_all_decays():
    mgr, _ = make_mgr()
    decays = [
        {"mother": 100, "daughters": [1,2]},
        {"mother": 100, "daughters": [1,3]},
    ]
    mgr.add_decays(decays, CalculationDecayStrategy.UFO, {"ufo_path": "/dev/null", "BR": False})
    # get_all_decays(None) -> dict
    all_dec = mgr.get_all_decays()
    assert (100, (1,2)) in all_dec and (100, (1,3)) in all_dec
    # get_all_decays(100) -> tuple lest (daugther)
    assert sorted(mgr.get_all_decays(100)) == [(1,2), (1,3)]


def test_lifetime_conversion_and_special_lifetime():
    # total width = 2.0 (UFO), lifetime invGeV = 0.5
    mgr, _ = make_mgr()
    mgr.add_decay(100, [1,2], CalculationDecayStrategy.UFO, {"ufo_path": "/dev/null", "BR": False})
    # without special lifetime -> 1/total
    tau_s = mgr.calculate_lifetime(100, Unit.S)
    assert tau_s == pytest.approx(br_mod.GEV_INV_TO_S / 2.0, rel=1e-12)

    # special lifetime : 1.0 mm
    mgr.add_special_lifetime(100, 1.0, Unit.MM)
    assert mgr.calculate_lifetime(100, Unit.MM) == pytest.approx(1.0, rel=1e-12)

    tau_s2 = mgr.calculate_lifetime(100, Unit.S)
    assert tau_s2 == pytest.approx(convert_lifetime(1.0, Unit.MM, Unit.S), rel=1e-12)


def test_manual_values_errors_and_direct_branching_ratio():
    mgr, _ = make_mgr()
    mgr.add_constant_decay(100, [1, 2], 0.25)
    mgr.add_constant_decay(100, [1, 3], 0.4, is_br=True)

    assert mgr.calculate_total_decay(100) == pytest.approx(0.25)
    assert mgr.calculate_branching_ratio_for_mother(100, [1, 2]) == pytest.approx(1.0)
    assert mgr.calculate_branching_ratio_for_mother(100, [1, 3]) == pytest.approx(0.4)

    with pytest.raises(ValueError, match="strictly positive"):
        mgr.add_special_lifetime(100, 0.0, Unit.S)
    with pytest.raises(ValueError, match="No decay registered"):
        mgr.calculate_decay(100, [2, 3])
    with pytest.raises(ValueError, match="No decay registered"):
        mgr.calculate_branching_ratio_for_mother(100, [2, 3])
    with pytest.raises(ValueError, match="No decays registered"):
        mgr.calculate_branching_ratios_for_mother(999)


def test_lifetime_requires_width_and_unit_conversions_cover_all_paths():
    mgr, _ = make_mgr()
    with pytest.raises(ValueError, match="No positive total decay width"):
        mgr.calculate_lifetime(100, Unit.S)

    assert convert_lifetime(2.0, Unit.S, Unit.S) == 2.0
    assert convert_lifetime(1.0, Unit.S, Unit.INVGEV) == pytest.approx(br_mod.S_TO_GEV_INV)
    assert convert_lifetime(1.0, Unit.INVGEV, Unit.MM) == pytest.approx(br_mod.GEV_INV_TO_MM)
    assert convert_lifetime(1.0, Unit.INVGEV, Unit.S) == pytest.approx(br_mod.GEV_INV_TO_S)


def test_madgraph_and_marty_strategy_configuration(monkeypatch):
    captured = {}

    class CapturingMadGraph(FakeAdapterBase):
        def __init__(self, calculator=None, is_br=False):
            super().__init__(is_br)
            captured["madgraph"] = (calculator, is_br)
        def calculate(self, *args): return 0.0

    class CapturingMarty(FakeAdapterBase):
        def __init__(self, model, model_name="SM", is_br=False):
            super().__init__(is_br)
            captured["marty"] = (model, model_name, is_br)
        def calculate(self, *args): return 0.0

    monkeypatch.setattr(br_mod, "MadGraphCalculationAdapter", CapturingMadGraph)
    monkeypatch.setattr(br_mod, "MartyCalculationAdapter", CapturingMarty)
    mgr, _ = make_mgr()
    calculator = lambda *_args: 0.0
    mgr.add_decay(100, [1, 2], CalculationDecayStrategy.MADGRAPH, {"calculator": calculator, "BR": True})
    mgr.add_decay(100, [1, 3], CalculationDecayStrategy.MARTY, {"model_name": "HNL"})

    assert captured["madgraph"] == (calculator, True)
    assert captured["marty"][0] is mgr.nsa
    assert captured["marty"][1:] == ("HNL", False)

    with pytest.raises(ValueError, match="Unknown decay calculation strategy"):
        mgr._create_strategy(object(), {})
